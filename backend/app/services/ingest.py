"""Registro dos atendimentos que o n8n já respondeu: conversa, mensagem do turista e resposta."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.models.tour import Tour
from app.services import message_handler
from app.services.message_handler import IncomingMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Exchange:
    """Um atendimento já respondido pelo n8n: o que o turista escreveu e o que foi enviado."""

    message_id: str
    phone: str
    text: str
    reply: str
    language: str | None
    suggested_tour_id: str | None
    needs_human: bool


@dataclass(frozen=True, slots=True)
class RecordedExchange:
    """Resultado do registro: `created` é falso quando o `message_id` já estava gravado."""

    created: bool
    conversation_id: str


async def _conversation_of(db: AsyncSession, message_id: str) -> str:
    """Conversa onde o `message_id` já foi gravado (a entrega repetida aponta para ela)."""
    result = await db.execute(
        select(Message.conversation_id).where(Message.whatsapp_message_id == message_id)
    )
    return result.scalar_one()


async def _active_tour_id(db: AsyncSession, tour_id: str | None) -> str | None:
    """O passeio sugerido é saída de terceiro: só vale se existir no catálogo e estiver ativo."""
    if tour_id is None:
        return None
    result = await db.execute(select(Tour.id).where(Tour.id == tour_id, Tour.ativo.is_(True)))
    if result.first() is None:
        logger.warning(
            "passeio sugerido fora do catálogo descartado", extra={"motivo": "allowlist"}
        )
        return None
    return tour_id


def _register_activity(conversation: Conversation, exchange: Exchange, tour_id: str | None) -> None:
    """Atualiza idioma, passeio e status; só escala o status (quem resolve é uma pessoa)."""
    if exchange.language is not None:
        conversation.idioma_detectado = exchange.language
    if tour_id is not None:
        conversation.passeio_sugerido_id = tour_id
    if exchange.needs_human:
        conversation.status = ConversationStatus.PRECISA_ATENCAO


async def _record(db: AsyncSession, exchange: Exchange) -> RecordedExchange:
    if await message_handler.is_duplicate_delivery(db, exchange.message_id):
        return RecordedExchange(False, await _conversation_of(db, exchange.message_id))

    conversation = await message_handler.get_or_create_open_conversation(db, exchange.phone)
    incoming = IncomingMessage(
        exchange.phone, "text", exchange.text, message_id=exchange.message_id
    )
    if not await message_handler.store_incoming(
        db, conversation, incoming, MessageType.TEXTO, exchange.text
    ):
        return RecordedExchange(False, await _conversation_of(db, exchange.message_id))

    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.SAIDA,
            tipo=MessageType.TEXTO,
            conteudo=exchange.reply,
            idioma=exchange.language,
        )
    )
    _register_activity(
        conversation, exchange, await _active_tour_id(db, exchange.suggested_tour_id)
    )
    await db.commit()
    return RecordedExchange(True, conversation.id)


async def record_exchange(db: AsyncSession, exchange: Exchange) -> RecordedExchange:
    """Grava o atendimento numa única transação; repetir o mesmo `message_id` não grava nada.

    O n8n já respondeu ao turista antes de chamar isto, então nada é enviado ao WhatsApp. Se algo
    falhar, a transação é desfeita por inteiro e a nova tentativa do n8n é processada do zero.

    Args:
        db: Sessão do banco.
        exchange: Atendimento já validado nas fronteiras.

    Returns:
        O resultado, com a conversa onde o atendimento está gravado.
    """
    try:
        return await _record(db, exchange)
    except Exception:
        await db.rollback()
        raise
