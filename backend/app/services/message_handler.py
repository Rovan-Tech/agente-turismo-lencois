from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.models.tour import Tour
from app.services import tour_matcher, whatsapp_client
from app.services.groq_client import (
    GroqReply,
    GroqUnavailableError,
    ask_groq,
    build_system_prompt,
)

logger = logging.getLogger(__name__)

# O idioma do turista ainda é desconhecido quando o áudio é recusado, então a resposta é trilíngue.
AUDIO_TOO_LONG_REPLY = (
    "Seu áudio é muito longo para eu ouvir. Pode mandar um áudio mais curto ou escrever? 🙏\n"
    "Your voice message is too long for me to listen to. Could you send a shorter one or type it?\n"
    "Tu audio es demasiado largo para escucharlo. ¿Puedes enviar uno más corto o escribirlo?"
)
# Contingência quando o Groq está fora do ar: o turista nunca fica sem resposta e a conversa vai
# para atendimento humano. Trilíngue pelo mesmo motivo do aviso de áudio.
GROQ_FALLBACK_REPLY = (
    "Estamos com dificuldade para responder agora. "
    "Uma pessoa da nossa equipe vai falar com você em breve.\n"
    "We are having trouble answering right now. Someone from our team will contact you soon.\n"
    "Estamos teniendo dificultades para responder ahora. "
    "Alguien de nuestro equipo te contactará pronto."
)
# Registro no painel: a agência vê que o turista mandou um áudio, mesmo sem transcrição. Vai como
# TEXTO porque o painel rotula AUDIO_TRANSCRITO como "transcrito de áudio".
AUDIO_TOO_LONG_NOTE = "[áudio muito longo — não transcrito]"


async def get_or_create_open_conversation(db: AsyncSession, phone: str) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_phone == phone)
        .where(Conversation.status != ConversationStatus.RESOLVIDA)
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalars().first()
    if conversation:
        return conversation

    conversation = Conversation(whatsapp_phone=phone)
    db.add(conversation)
    await db.flush()
    return conversation


async def resolve_incoming_text(
    settings: Settings, message_type: str, text_body: str | None, media_id: str | None
) -> tuple[str, MessageType]:
    if message_type == "text":
        return text_body or "", MessageType.TEXTO

    if message_type == "audio" and media_id:
        media_url = await whatsapp_client.get_media_url(settings, media_id)
        audio_bytes = await whatsapp_client.download_media(
            settings, media_url, settings.max_audio_bytes
        )

        from app.services.transcription import transcribe_audio

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            text, _language = transcribe_audio(settings, tmp_file.name)
        return text, MessageType.AUDIO_TRANSCRITO

    return "", MessageType.TEXTO


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """Mensagem recebida do WhatsApp, já extraída do payload do webhook."""

    phone: str
    message_type: str
    text_body: str | None = None
    media_id: str | None = None
    message_id: str | None = None


async def _is_duplicate(db: AsyncSession, whatsapp_message_id: str | None) -> bool:
    """Diz se a Meta já entregou (e nós já registramos) uma mensagem com este id."""
    if not whatsapp_message_id:
        return False
    result = await db.execute(
        select(Message.id).where(Message.whatsapp_message_id == whatsapp_message_id)
    )
    return result.first() is not None


async def _store_incoming(
    db: AsyncSession,
    conversation: Conversation,
    incoming: IncomingMessage,
    tipo: MessageType,
    content: str,
) -> bool:
    """Grava a mensagem do turista já, para que o índice único barre reenvios simultâneos.

    Returns:
        `False` se outra entrega do mesmo `message_id` chegou antes (a transação é desfeita).
    """
    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.ENTRADA,
            tipo=tipo,
            conteudo=content,
            whatsapp_message_id=incoming.message_id,
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        if incoming.message_id is None:
            raise  # sem id não há duplicata: é outra constraint, não pode sumir em silêncio
        logger.info("entrega duplicada descartada")
        return False
    return True


async def _send_then_commit(db: AsyncSession, settings: Settings, phone: str, body: str) -> None:
    """Envia a resposta e só então confirma a transação.

    Se o envio falhar, nada fica gravado (nem o `message_id`), então o reenvio do webhook pela
    Meta é processado em vez de descartado como duplicado e o turista não fica sem resposta.
    """
    await whatsapp_client.send_text_message(settings, phone, body)
    await db.commit()


async def _refuse_oversized_audio(
    db: AsyncSession, settings: Settings, conversation: Conversation, incoming: IncomingMessage
) -> Conversation | None:
    """Registra o áudio recusado e avisa o turista, sem transcrever nem chamar o Groq."""
    if not await _store_incoming(
        db, conversation, incoming, MessageType.TEXTO, AUDIO_TOO_LONG_NOTE
    ):
        return None
    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.SAIDA,
            tipo=MessageType.TEXTO,
            conteudo=AUDIO_TOO_LONG_REPLY,
        )
    )
    # Sem telefone nem conteúdo no log (LGPD): serve só para medir quantos turistas batem no teto.
    logger.info("áudio recusado: acima de %d bytes", settings.max_audio_bytes)
    await _send_then_commit(db, settings, incoming.phone, AUDIO_TOO_LONG_REPLY)
    return conversation


async def _generate_reply(db: AsyncSession, settings: Settings, content: str) -> GroqReply:
    """Escolhe os passeios candidatos, pede a resposta ao Groq e valida o passeio que ele sugeriu.

    O `id` sugerido é saída de terceiro: só vale se estiver entre os candidatos que o modelo viu.
    """
    result = await db.execute(select(Tour).where(Tour.ativo.is_(True)))
    candidate_tours = tour_matcher.select_candidate_tours(list(result.scalars().all()), content)
    system_prompt = build_system_prompt(settings.agency_name, candidate_tours)
    try:
        reply = await ask_groq(settings, system_prompt, content)
    except GroqUnavailableError as error:
        # A causa vai no texto (o formato padrão de log descarta o `extra`) e também estruturada.
        logger.warning(
            "Groq indisponível: causa=%s status_http=%s; resposta de contingência",
            error.causa,
            error.status_http,
            extra={"motivo": "groq", "causa": error.causa, "status_http": error.status_http},
        )
        # Sem idioma: a contingência não sabe em que língua o turista escreve e não pode apagar
        # o idioma já detectado nem inventar um.
        return GroqReply(idioma=None, precisa_atencao_humana=True, resposta=GROQ_FALLBACK_REPLY)
    offered = {tour.id for tour in candidate_tours}
    if reply.passeio_sugerido_id is not None and reply.passeio_sugerido_id not in offered:
        logger.warning(
            "passeio sugerido fora dos candidatos descartado", extra={"motivo": "allowlist"}
        )
        reply.passeio_sugerido_id = None
    return reply


def _record_reply(db: AsyncSession, conversation: Conversation, reply: GroqReply) -> None:
    """Persiste a resposta do bot e atualiza idioma e status da conversa conforme o Groq decidiu."""
    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.SAIDA,
            tipo=MessageType.TEXTO,
            conteudo=reply.resposta,
            idioma=reply.idioma,
        )
    )
    if reply.idioma is not None:
        conversation.idioma_detectado = reply.idioma
    if reply.passeio_sugerido_id is not None:
        conversation.passeio_sugerido_id = reply.passeio_sugerido_id
    conversation.status = (
        ConversationStatus.PRECISA_ATENCAO
        if reply.precisa_atencao_humana
        else ConversationStatus.ABERTA
    )


async def process_incoming_message(
    db: AsyncSession, settings: Settings, incoming: IncomingMessage
) -> Conversation | None:
    """Processa uma mensagem do turista: registra, pede a resposta ao Groq e a envia.

    Áudio acima de `max_audio_bytes` é recusado com um aviso, sem transcrever nem chamar o Groq.
    A Meta reenvia o webhook quando demora; uma mensagem cujo `message_id` já foi registrada é
    ignorada, sem baixar áudio, chamar o Groq nem responder de novo. A resposta é enviada antes do
    `commit`: se o envio falhar, a exceção sobe (a Meta reenvia) e nada fica gravado.

    Args:
        db: Sessão do banco.
        settings: Configuração da aplicação.
        incoming: Mensagem extraída do payload do webhook.

    Returns:
        A conversa atualizada, ou `None` se a mensagem era uma entrega repetida.
    """
    if await _is_duplicate(db, incoming.message_id):
        return None
    conversation = await get_or_create_open_conversation(db, incoming.phone)

    try:
        content, tipo = await resolve_incoming_text(
            settings, incoming.message_type, incoming.text_body, incoming.media_id
        )
    except whatsapp_client.MediaTooLargeError:
        return await _refuse_oversized_audio(db, settings, conversation, incoming)

    if not await _store_incoming(db, conversation, incoming, tipo, content):
        return None

    reply = await _generate_reply(db, settings, content)
    _record_reply(db, conversation, reply)
    await _send_then_commit(db, settings, incoming.phone, reply.resposta)
    return conversation
