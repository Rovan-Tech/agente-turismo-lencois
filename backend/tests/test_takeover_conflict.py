"""Duas pessoas querendo assumir a mesma conversa: só a primeira consegue (ADR-0008)."""

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app
from app.models.message import Message, MessageAuthor
from app.services import whatsapp_client
from tests.handoff_support import Outbox, all_messages, take_over

pytestmark = pytest.mark.asyncio

HELD_BY_ANA = "A conversa já está com Ana. Peça para devolver à IA."


@pytest.fixture
def ana_token(access):
    return access.token(sub="ana-1", email="ana.souza@rovantech.com")


@pytest.fixture
def bia_token(access):
    return access.token(sub="bia-2", email="bia.lima@rovantech.com")


async def _attendant_messages(db_session: AsyncSession) -> list[Message]:
    return [m for m in await all_messages(db_session) if m.autor == MessageAuthor.ATENDENTE]


async def test_second_attendant_is_refused_clearly_and_the_conversation_stays_with_the_first(
    client, db_session, access, conversation, outbox, ana_token, bia_token
):
    first = await take_over(client, access, conversation, ana_token)

    second = await take_over(client, access, conversation, bia_token)

    assert (first.status_code, first.json()["atendente_sub"]) == (200, "ana-1")
    assert (second.status_code, second.json()) == (409, {"detail": HELD_BY_ANA})
    await db_session.refresh(conversation)
    assert (conversation.atendimento, conversation.humano_sub) == ("humano", "ana-1")
    assert conversation.humano_nome == "Ana"
    assert len(outbox.sent) == 1
    assert [m.autor_sub for m in await _attendant_messages(db_session)] == ["ana-1"]


async def test_second_attendant_is_refused_again_on_every_retry(
    client, access, conversation, outbox, ana_token, bia_token
):
    await take_over(client, access, conversation, ana_token)

    retries = [await take_over(client, access, conversation, bia_token) for _ in range(3)]

    assert [r.status_code for r in retries] == [409, 409, 409]
    assert len(outbox.sent) == 1


async def test_the_first_attendant_can_take_over_again_without_a_new_announcement(
    client, access, conversation, outbox, ana_token, bia_token
):
    await take_over(client, access, conversation, ana_token)
    await take_over(client, access, conversation, bia_token)

    again = await take_over(client, access, conversation, ana_token)

    assert (again.status_code, len(outbox.sent)) == (200, 1)


@pytest.fixture
def slow_outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """WhatsApp que demora a responder: dá tempo de a segunda pessoa chegar durante o envio."""
    box = Outbox()

    async def slow_send(settings: object, to: str, body: str) -> None:
        await asyncio.sleep(0.3)
        box.sent.append((to, body))

    monkeypatch.setattr(whatsapp_client, "send_text_message", slow_send)
    return box


@pytest_asyncio.fixture
async def one_connection_per_request(client):
    """Cada requisição com a própria conexão, como em produção (o `client` divide uma sessão)."""
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def per_request_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = per_request_db
    yield
    await engine.dispose()


# O SQLite ignora `FOR UPDATE` e não tem duas conexões reais na memória: só o PostgreSQL (job
# `backend` do CI, sempre com `TEST_DATABASE_URL`) exercita a trava de linha de verdade.
@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="a trava de linha (FOR UPDATE) só existe no PostgreSQL",
)
async def test_two_attendants_taking_over_at_the_same_time_only_one_wins(
    client,
    db_session,
    access,
    conversation,
    slow_outbox,
    one_connection_per_request,
    ana_token,
    bia_token,
):
    responses = await asyncio.gather(
        take_over(client, access, conversation, ana_token),
        take_over(client, access, conversation, bia_token),
    )

    won = [r for r in responses if r.status_code == 200]
    lost = [r for r in responses if r.status_code == 409]
    assert (len(won), len(lost)) == (1, 1)
    winner_sub = won[0].json()["atendente_sub"]
    winner_name = won[0].json()["atendente_nome"]
    assert lost[0].json() == {
        "detail": f"A conversa já está com {winner_name}. Peça para devolver à IA."
    }
    await db_session.refresh(conversation)
    assert conversation.humano_sub == winner_sub
    assert len(slow_outbox.sent) == 1
    saved = await db_session.execute(select(Message.autor_sub).where(Message.autor == "atendente"))
    assert saved.scalars().all() == [winner_sub]
