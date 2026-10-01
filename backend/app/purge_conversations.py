"""Expurgo de conversas inativas (LGPD, ADR-0005).

Rodar com: python -m app.purge_conversations
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory, engine
from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)


async def purge_expired_conversations(
    db: AsyncSession, retention_days: int, *, now: datetime | None = None
) -> int:
    """Apaga as conversas sem atividade há mais de `retention_days`, junto com as mensagens.

    O texto do turista também pode ter dado pessoal, então a conversa vai inteira. Repetir é
    seguro: o que já foi apagado não volta a casar.

    Args:
        db: Sessão do banco.
        retention_days: Dias de inatividade tolerados (`updated_at`).
        now: Instante de referência (UTC); o padrão é agora.

    Returns:
        Quantas conversas foram apagadas. O log traz só esse número, nunca telefone nem texto.
    """
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    expired = select(Conversation.id).where(Conversation.updated_at < cutoff)
    await db.execute(
        delete(Message)
        .where(Message.conversation_id.in_(expired))
        .execution_options(synchronize_session=False)
    )
    deleted = await db.execute(
        delete(Conversation)
        .where(Conversation.updated_at < cutoff)
        .returning(Conversation.id)
        .execution_options(synchronize_session=False)
    )
    count = len(deleted.all())
    await db.commit()
    logger.info(
        "expurgo de conversas: %d apagadas",
        count,
        extra={"event": "conversations_purged", "count": count, "retention_days": retention_days},
    )
    return count


async def main() -> None:
    """Expurga com o prazo configurado em `CONVERSATION_RETENTION_DAYS` e registra o total."""
    logging.basicConfig(level=logging.INFO)
    retention_days = get_settings().conversation_retention_days
    async with async_session_factory() as db:
        await purge_expired_conversations(db, retention_days)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
