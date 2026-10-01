"""Atendimento humano: uma pessoa assume a conversa e responde no lugar da IA (ADR-0008).

As regras ficam aqui e as rotas só traduzem: o destinatário é sempre o telefone da conversa, o
aviso ao turista é um modelo fixo, o envio vem antes da gravação e nada do que o WhatsApp devolve
vai para a resposta ou para o log além do código do erro.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_jwt import AccessIdentity
from app.core.config import Settings
from app.models.conversation import Conversation, ConversationStatus, Handling
from app.models.message import Message, MessageAuthor, MessageDirection
from app.services import whatsapp_client
from app.services.handoff_texts import announcement_text, give_back_text

logger = logging.getLogger(__name__)

# A Meta só aceita texto livre até 24 h depois da última mensagem do turista (erro 131047).
WINDOW = timedelta(hours=24)
WINDOW_CLOSED = (
    "A última mensagem do turista tem mais de 24 horas: o WhatsApp só permite responder dentro "
    "desse prazo. Espere o turista escrever de novo."
)


class HandoffError(Exception):
    """Pedido recusado por uma regra do atendimento; `status_code` é o que a rota devolve."""

    def __init__(self, status_code: int, detail: str) -> None:
        """Guarda o status HTTP e o motivo, já escritos para quem usa o painel."""
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class OutgoingText:
    """Texto digitado pelo atendente e o id que o painel gerou para este envio."""

    text: str
    client_message_id: str


def _aware(moment: datetime) -> datetime:
    """O SQLite devolve datas sem fuso (sempre UTC aqui); o Postgres já devolve com fuso."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def current_handling(conversation: Conversation, settings: Settings) -> Handling:
    """Quem responde agora: `humano` só até `human_handoff_idle_hours` sem mensagem do atendente.

    A devolução à IA é calculada na hora da consulta, sem tarefa agendada.
    """
    last_activity = conversation.humano_atividade_em or conversation.humano_desde
    if conversation.atendimento != Handling.HUMANO or last_activity is None:
        return Handling.IA
    idle = datetime.now(UTC) - _aware(last_activity)
    return (
        Handling.HUMANO
        if idle < timedelta(hours=settings.human_handoff_idle_hours)
        else Handling.IA
    )


async def window_is_open(db: AsyncSession, conversation: Conversation) -> bool:
    """Diz se a última mensagem do turista tem menos de 24 horas (texto livre ainda permitido)."""
    result = await db.execute(
        select(func.max(Message.created_at)).where(
            Message.conversation_id == conversation.id, Message.autor == MessageAuthor.TURISTA
        )
    )
    last = result.scalar_one()
    return last is not None and datetime.now(UTC) - _aware(last) <= WINDOW


async def _deliver(settings: Settings, phone: str, text: str) -> None:
    """Envia pelo WhatsApp; a falha vira 502 só com o código da Meta (sem URL, token ou corpo)."""
    try:
        await whatsapp_client.send_text_message(settings, phone, text)
    except httpx.HTTPError as error:
        code = _meta_error_code(error)
        # O texto da exceção do httpx traz a URL com o phone_number_id: só tipo e código vão ao log.
        logger.warning(
            "falha ao enviar pelo WhatsApp: %s (código %s)",
            type(error).__name__,
            code,
            extra={"event": "handoff_delivery_failed", "error_type": type(error).__name__},
        )
        suffix = f" (código {code} da Meta)" if code else ""
        raise HandoffError(
            502, f"Não foi possível enviar a mensagem pelo WhatsApp{suffix}."
        ) from None


def _meta_error_code(error: httpx.HTTPError) -> int | None:
    """Código numérico do erro da Meta (como 131047), ou `None` se não houver um."""
    if not isinstance(error, httpx.HTTPStatusError):
        return None
    try:
        code = error.response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return None
    return code if isinstance(code, int) and not isinstance(code, bool) else None


def _attendant_message(
    conversation: Conversation, identity: AccessIdentity, text: str, client_message_id: str | None
) -> Message:
    return Message(
        conversation_id=conversation.id,
        direction=MessageDirection.SAIDA,
        autor=MessageAuthor.ATENDENTE,
        autor_sub=identity.sub,
        conteudo=text,
        idioma=conversation.idioma_detectado,
        client_message_id=client_message_id,
    )


def _holder_name(conversation: Conversation) -> str:
    return conversation.humano_nome or "outra pessoa da equipe"


def clear_handling(conversation: Conversation) -> None:
    """Volta a conversa para a IA e esquece quem estava atendendo."""
    conversation.atendimento = Handling.IA
    conversation.humano_sub = None
    conversation.humano_nome = None
    conversation.humano_desde = None
    conversation.humano_atividade_em = None


async def take_over(
    db: AsyncSession, settings: Settings, conversation: Conversation, identity: AccessIdentity
) -> Conversation:
    """A pessoa assume: o turista é avisado antes e só então a conversa muda para `humano`.

    Raises:
        HandoffError: 409 se estiver resolvida, com outra pessoa ou fora da janela de 24 h; 502 se o
            WhatsApp recusar o aviso (a conversa continua com a IA).
    """
    if conversation.status == ConversationStatus.RESOLVIDA:
        raise HandoffError(409, "A conversa já foi resolvida. Reabra-a para assumir.")
    now = datetime.now(UTC)
    if current_handling(conversation, settings) == Handling.HUMANO:
        if conversation.humano_sub != identity.sub:
            holder = _holder_name(conversation)
            raise HandoffError(409, f"A conversa já está com {holder}. Peça para devolver à IA.")
        conversation.humano_atividade_em = now
        await db.commit()
        return conversation
    if not await window_is_open(db, conversation):
        raise HandoffError(409, WINDOW_CLOSED)
    text = announcement_text(conversation.idioma_detectado, identity.first_name)
    await _deliver(settings, conversation.whatsapp_phone, text)
    conversation.atendimento = Handling.HUMANO
    conversation.humano_sub = identity.sub
    conversation.humano_nome = identity.first_name
    conversation.humano_desde = conversation.humano_atividade_em = now
    db.add(_attendant_message(conversation, identity, text, None))
    await db.commit()
    return conversation


async def give_back(
    db: AsyncSession, settings: Settings, conversation: Conversation, identity: AccessIdentity
) -> Conversation:
    """Devolve a conversa para a IA e avisa o turista, se ainda der para falar com ele.

    Sempre devolve: se a janela de 24 h fechou ou o WhatsApp recusar o aviso, o aviso é pulado
    (o turista nunca fica sem a IA por causa disso).
    """
    text = give_back_text(conversation.idioma_detectado)
    was_human = current_handling(conversation, settings) == Handling.HUMANO
    if was_human and await window_is_open(db, conversation):
        try:
            await _deliver(settings, conversation.whatsapp_phone, text)
            db.add(_attendant_message(conversation, identity, text, None))
        except HandoffError:
            logger.warning("aviso de devolução à IA não enviado", extra={"event": "handoff_notice"})
    clear_handling(conversation)
    await db.commit()
    return conversation


async def _select_by_client_id(db: AsyncSession, client_message_id: str) -> Message | None:
    result = await db.execute(select(Message).where(Message.client_message_id == client_message_id))
    return result.scalar_one_or_none()


async def find_by_client_message_id(db: AsyncSession, client_message_id: str) -> Message | None:
    """Mensagem já enviada com este id do painel (a repetição devolve o resultado da primeira)."""
    return await _select_by_client_id(db, client_message_id)


async def _check_can_send(
    db: AsyncSession, settings: Settings, conversation: Conversation, identity: AccessIdentity
) -> None:
    if conversation.status == ConversationStatus.RESOLVIDA:
        raise HandoffError(409, "A conversa já foi resolvida.")
    if current_handling(conversation, settings) != Handling.HUMANO:
        raise HandoffError(409, "Assuma a conversa antes de responder (a IA voltou a atender).")
    if conversation.humano_sub != identity.sub:
        raise HandoffError(409, f"A conversa está com {_holder_name(conversation)}.")
    if not await window_is_open(db, conversation):
        raise HandoffError(409, WINDOW_CLOSED)
    since = datetime.now(UTC) - timedelta(hours=1)
    sent = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.autor == MessageAuthor.ATENDENTE,
            Message.created_at >= since,
        )
    )
    if sent.scalar_one() >= settings.human_send_cap_per_hour:
        raise HandoffError(
            429, "Limite de mensagens por hora nesta conversa atingido. Tente mais tarde."
        )


def _replay(existing: Message, conversation_id: str) -> Message:
    """A repetição de um envio devolve a mensagem original, mas só dentro da mesma conversa."""
    if existing.conversation_id != conversation_id:
        raise HandoffError(409, "Este envio já foi usado em outra conversa.")
    return existing


async def send_message(
    db: AsyncSession,
    settings: Settings,
    conversation: Conversation,
    identity: AccessIdentity,
    outgoing: OutgoingText,
) -> Message:
    """Envia a resposta do atendente ao telefone da conversa e a grava, uma vez por envio.

    A linha é reservada antes (o índice único de `client_message_id` barra dois cliques
    simultâneos), o WhatsApp recebe em seguida e só então a transação é confirmada: se a Meta
    recusar, nada fica gravado.

    Raises:
        HandoffError: 409 sem estar com a pessoa, resolvida ou fora da janela de 24 h; 429 acima do
            teto por hora; 502 se o WhatsApp recusar.
    """
    # Guardado antes: o rollback de um conflito expira o objeto e ler `.id` depois exigiria I/O.
    conversation_id = conversation.id
    existing = await find_by_client_message_id(db, outgoing.client_message_id)
    if existing:
        return _replay(existing, conversation_id)
    await _check_can_send(db, settings, conversation, identity)
    message = _attendant_message(conversation, identity, outgoing.text, outgoing.client_message_id)
    db.add(message)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        winner = await _select_by_client_id(db, outgoing.client_message_id)
        if winner is None:
            raise
        return _replay(winner, conversation_id)
    try:
        await _deliver(settings, conversation.whatsapp_phone, outgoing.text)
    except HandoffError:
        await db.rollback()
        raise
    conversation.humano_atividade_em = datetime.now(UTC)
    await db.commit()
    return message


async def find_open_conversation(db: AsyncSession, phone: str) -> Conversation | None:
    """A conversa não resolvida mais recente deste telefone, se houver."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_phone == phone)
        .where(Conversation.status != ConversationStatus.RESOLVIDA)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().first()


async def handling_for_phone(db: AsyncSession, settings: Settings, phone: str) -> Handling:
    """Quem responde à conversa aberta deste telefone (o n8n pergunta antes de chamar o Gemini)."""
    conversation = await find_open_conversation(db, phone)
    return current_handling(conversation, settings) if conversation else Handling.IA
