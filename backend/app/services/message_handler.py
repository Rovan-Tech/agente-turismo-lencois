from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.models.tour import Tour
from app.services import tour_matcher, whatsapp_client
from app.services.groq_client import GroqReply, ask_groq, build_system_prompt

logger = logging.getLogger(__name__)

# O idioma do turista ainda é desconhecido quando o áudio é recusado, então a resposta é trilíngue.
AUDIO_TOO_LONG_REPLY = (
    "Seu áudio é muito longo para eu ouvir. Pode mandar um áudio mais curto ou escrever? 🙏\n"
    "Your voice message is too long for me to listen to. Could you send a shorter one or type it?\n"
    "Tu audio es demasiado largo para escucharlo. ¿Puedes enviar uno más corto o escribirlo?"
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


async def _refuse_oversized_audio(
    db: AsyncSession, settings: Settings, conversation: Conversation, phone: str
) -> Conversation:
    """Registra o áudio recusado e avisa o turista, sem transcrever nem chamar o Groq."""
    db.add_all(
        [
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.ENTRADA,
                tipo=MessageType.TEXTO,
                conteudo=AUDIO_TOO_LONG_NOTE,
            ),
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.SAIDA,
                tipo=MessageType.TEXTO,
                conteudo=AUDIO_TOO_LONG_REPLY,
            ),
        ]
    )
    await db.commit()
    # Sem telefone nem conteúdo no log (LGPD): serve só para medir quantos turistas batem no teto.
    logger.info("áudio recusado: acima de %d bytes", settings.max_audio_bytes)
    await whatsapp_client.send_text_message(settings, phone, AUDIO_TOO_LONG_REPLY)
    return conversation


async def _generate_reply(db: AsyncSession, settings: Settings, content: str) -> GroqReply:
    """Escolhe os passeios candidatos para a mensagem e pede a resposta ao Groq."""
    result = await db.execute(select(Tour).where(Tour.ativo.is_(True)))
    candidate_tours = tour_matcher.select_candidate_tours(list(result.scalars().all()), content)
    system_prompt = build_system_prompt(settings.agency_name, candidate_tours)
    return await ask_groq(settings, system_prompt, content)


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
    conversation.idioma_detectado = reply.idioma
    conversation.status = (
        ConversationStatus.PRECISA_ATENCAO
        if reply.precisa_atencao_humana
        else ConversationStatus.ABERTA
    )


async def process_incoming_message(
    db: AsyncSession, settings: Settings, incoming: IncomingMessage
) -> Conversation:
    """Processa uma mensagem do turista: registra, pede a resposta ao Groq e a envia.

    Áudio acima de `max_audio_bytes` é recusado com um aviso, sem transcrever nem chamar o Groq.

    Args:
        db: Sessão do banco.
        settings: Configuração da aplicação.
        incoming: Mensagem extraída do payload do webhook.

    Returns:
        A conversa atualizada.
    """
    conversation = await get_or_create_open_conversation(db, incoming.phone)

    try:
        content, tipo = await resolve_incoming_text(
            settings, incoming.message_type, incoming.text_body, incoming.media_id
        )
    except whatsapp_client.MediaTooLargeError:
        return await _refuse_oversized_audio(db, settings, conversation, incoming.phone)

    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.ENTRADA,
            tipo=tipo,
            conteudo=content,
        )
    )

    reply = await _generate_reply(db, settings, content)

    _record_reply(db, conversation, reply)

    await db.commit()

    await whatsapp_client.send_text_message(settings, incoming.phone, reply.resposta)

    return conversation
