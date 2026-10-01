"""Retenção de 90 dias das conversas (ADR-0005, LGPD): apaga a conversa e as mensagens dela."""

import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection
from app.purge_conversations import purge_expired_conversations
from tests.ingest_support import app_log_text

RETENTION_DAYS = 90
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


async def _add_conversation(
    db: AsyncSession,
    phone: str,
    *,
    idle_days: int,
    status: ConversationStatus = ConversationStatus.ABERTA,
    language: str | None = None,
) -> Conversation:
    conversation = Conversation(
        whatsapp_phone=phone,
        status=status,
        idioma_detectado=language,
        updated_at=NOW - timedelta(days=idle_days),
    )
    db.add(conversation)
    await db.flush()
    for direction in (MessageDirection.ENTRADA, MessageDirection.SAIDA):
        db.add(Message(conversation_id=conversation.id, direction=direction, conteudo="texto"))
    await db.commit()
    return conversation


async def _phones(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Conversation.whatsapp_phone).order_by(Conversation.created_at))
    return list(result.scalars().all())


async def _purge(db: AsyncSession) -> int:
    return await purge_expired_conversations(db, RETENTION_DAYS, now=NOW)


@pytest.mark.asyncio
async def test_purge_deletes_conversations_inactive_over_retention_with_their_messages(db_session):
    old = await _add_conversation(db_session, "5598900000001", idle_days=91)
    await _add_conversation(db_session, "5598900000002", idle_days=1)

    deleted = await _purge(db_session)

    assert deleted == 1
    assert await _phones(db_session) == ["5598900000002"]
    orphans = await db_session.execute(select(Message).where(Message.conversation_id == old.id))
    assert orphans.scalars().all() == []


@pytest.mark.asyncio
async def test_purge_keeps_conversations_with_recent_activity(db_session):
    await _add_conversation(db_session, "5598900000003", idle_days=89)
    await _add_conversation(db_session, "5598900000004", idle_days=RETENTION_DAYS)

    deleted = await _purge(db_session)

    assert deleted == 0
    assert len(await _phones(db_session)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", list(ConversationStatus))
async def test_purge_deletes_old_conversations_in_any_status(db_session, status):
    await _add_conversation(db_session, "5598900000005", idle_days=200, status=status)

    assert await _purge(db_session) == 1
    assert await _phones(db_session) == []


@pytest.mark.asyncio
async def test_purge_is_idempotent(db_session):
    await _add_conversation(db_session, "5598900000006", idle_days=120)

    assert await _purge(db_session) == 1
    assert await _purge(db_session) == 0


@pytest.mark.asyncio
async def test_purge_logs_only_the_count(db_session, caplog):
    caplog.set_level(logging.DEBUG)
    await _add_conversation(db_session, "5598911110001", idle_days=120)

    await _purge(db_session)

    logged = app_log_text(caplog)
    assert "5598911110001" not in logged
    assert "1 apagadas" in logged


@pytest.mark.asyncio
async def test_main_purges_with_the_configured_retention(db_session, monkeypatch):
    from app import purge_conversations
    from app.core.config import get_settings

    class _Session:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *exc_info):
            return None

    class _Engine:
        disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    engine = _Engine()
    monkeypatch.setattr(get_settings(), "conversation_retention_days", 30)
    monkeypatch.setattr(purge_conversations, "async_session_factory", _Session)
    monkeypatch.setattr(purge_conversations, "engine", engine)
    await _add_conversation(db_session, "5598900000007", idle_days=45)
    await _add_conversation(db_session, "5598900000008", idle_days=5)
    monkeypatch.setattr(
        purge_conversations,
        "purge_expired_conversations",
        _with_fixed_now(purge_conversations.purge_expired_conversations),
    )

    await purge_conversations.main()

    assert await _phones(db_session) == ["5598900000008"]
    assert engine.disposed is True


def _with_fixed_now(purge):
    async def runner(db, retention_days):
        return await purge(db, retention_days, now=NOW)

    return runner


@pytest.mark.asyncio
async def test_purge_keeps_a_conversation_that_got_a_legacy_webhook_message_today(
    db_session, pipeline_spies
):
    from datetime import datetime

    from app.core.config import get_settings
    from app.services.message_handler import IncomingMessage, process_incoming_message

    # Mesmo idioma e status que o bot vai gravar: sem mudança de coluna o ORM não gera UPDATE.
    conversation = await _add_conversation(
        db_session, "5598900000009", idle_days=100, language="pt"
    )
    incoming = IncomingMessage("5598900000009", "text", "oi", message_id="wamid.legado")
    await process_incoming_message(db_session, get_settings(), incoming)

    deleted = await purge_expired_conversations(db_session, RETENTION_DAYS, now=datetime.now(UTC))

    assert deleted == 0
    assert await _phones(db_session) == ["5598900000009"]
    assert conversation.id
