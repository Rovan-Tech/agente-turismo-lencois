"""Comportamento do endpoint que registra os atendimentos feitos pelo n8n (ADR-0005)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection
from app.models.tour import Tour
from tests.ingest_support import post_exchange

pytestmark = pytest.mark.usefixtures("ingest_token")

OPEN = ConversationStatus.ABERTA
ATTENTION = ConversationStatus.PRECISA_ATENCAO


async def _conversations(db: AsyncSession) -> list[Conversation]:
    result = await db.execute(select(Conversation).order_by(Conversation.created_at))
    return list(result.scalars().all())


async def _messages(db: AsyncSession) -> list[Message]:
    result = await db.execute(select(Message).order_by(Message.created_at, Message.id))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_ingest_creates_the_conversation_with_the_tourist_message_and_the_reply(
    client, db_session
):
    response = await post_exchange(client)

    assert response.status_code == 200
    (conversation,) = await _conversations(db_session)
    assert response.json() == {"status": "criado", "conversa_id": conversation.id}
    assert (conversation.whatsapp_phone, conversation.idioma_detectado) == ("5598900000001", "pt")
    messages = await _messages(db_session)
    assert {(m.direction, m.conteudo) for m in messages} == {
        (MessageDirection.ENTRADA, "Vou com minha avó de 78 anos, qual passeio indicam?"),
        (MessageDirection.SAIDA, "O passeio de bugre pela orla é o mais tranquilo."),
    }
    inbound = next(m for m in messages if m.direction == MessageDirection.ENTRADA)
    assert inbound.whatsapp_message_id == "wamid.teste-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("previous_status", "conversations_after"),
    [(OPEN, 1), (ConversationStatus.RESOLVIDA, 2)],
    ids=["reuses_the_open_one", "opens_a_new_one_after_resolved"],
)
async def test_ingest_picks_the_conversation_by_phone_and_status(
    client, db_session, previous_status, conversations_after
):
    await post_exchange(client, whatsapp_message_id="wamid.a")
    (first,) = await _conversations(db_session)
    first.status = previous_status
    await db_session.commit()

    await post_exchange(client, whatsapp_message_id="wamid.b")

    assert len(await _conversations(db_session)) == conversations_after


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_flag", "second_flag", "expected"),
    [
        (False, False, OPEN),
        (False, True, ATTENTION),
        (True, False, ATTENTION),
        (True, True, ATTENTION),
    ],
    ids=["stays_open", "escalates", "false_does_not_clear", "stays_escalated"],
)
async def test_ingest_status_only_escalates_and_never_resolves(
    client, db_session, first_flag, second_flag, expected
):
    await post_exchange(client, whatsapp_message_id="wamid.a", precisa_atencao_humana=first_flag)

    await post_exchange(client, whatsapp_message_id="wamid.b", precisa_atencao_humana=second_flag)

    (conversation,) = await _conversations(db_session)
    assert conversation.status == expected


@pytest.mark.asyncio
async def test_ingest_keeps_the_detected_language_when_the_new_one_is_null(client, db_session):
    await post_exchange(client, whatsapp_message_id="wamid.a", idioma="es")

    await post_exchange(client, whatsapp_message_id="wamid.b", idioma=None)

    (conversation,) = await _conversations(db_session)
    assert conversation.idioma_detectado == "es"


@pytest.mark.asyncio
async def test_ingest_records_the_suggested_tour_when_it_is_active(
    client, db_session, sample_tours
):
    db_session.add_all(sample_tours)
    await db_session.commit()

    await post_exchange(client, passeio_sugerido_id="rio-preguicas")

    (conversation,) = await _conversations(db_session)
    assert conversation.passeio_sugerido_id == "rio-preguicas"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tour_id",
    ["id-que-nao-existe", "x'; DROP TABLE tours; --", "inativo"],
    ids=["unknown", "sql_payload", "inactive"],
)
async def test_ingest_drops_a_suggested_tour_that_is_not_an_active_catalog_entry(
    client, db_session, sample_tours, tour_id
):
    sample_tours[0].id = "inativo"
    sample_tours[0].ativo = False
    db_session.add_all(sample_tours)
    await db_session.commit()

    response = await post_exchange(client, passeio_sugerido_id=tour_id)

    assert response.status_code == 200
    (conversation,) = await _conversations(db_session)
    assert conversation.passeio_sugerido_id is None
    assert len(await _messages(db_session)) == 2


@pytest.mark.asyncio
async def test_ingest_does_not_touch_the_tours(client, db_session, sample_tours):
    db_session.add_all(sample_tours)
    await db_session.commit()

    async def snapshot() -> list[dict[str, object]]:
        result = await db_session.execute(select(Tour).order_by(Tour.id))
        return [t.to_catalog_dict() | {"ativo": t.ativo} for t in result.scalars().all()]

    before = await snapshot()

    await post_exchange(client, passeio_sugerido_id="rio-preguicas")

    assert await snapshot() == before


@pytest.mark.asyncio
async def test_ingest_replay_returns_duplicate_and_writes_nothing(client, db_session):
    first = await post_exchange(client)

    replay = await post_exchange(client)

    assert replay.status_code == 200
    assert replay.json() == {"status": "duplicado", "conversa_id": first.json()["conversa_id"]}
    assert len(await _conversations(db_session)) == 1
    assert len(await _messages(db_session)) == 2


@pytest.mark.asyncio
async def test_ingest_concurrent_same_message_id_writes_once(
    client, db_session, blind_duplicate_check
):
    first = await post_exchange(client)

    second = await post_exchange(client)

    assert second.json() == {"status": "duplicado", "conversa_id": first.json()["conversa_id"]}
    assert len(await _messages(db_session)) == 2


class _DatabaseDownError(Exception):
    """Simula o banco fora do ar no momento do commit."""


@pytest.mark.asyncio
async def test_ingest_retry_after_failure_writes_once(client, db_session, monkeypatch):
    real_commit = db_session.commit

    async def failing_commit() -> None:
        raise _DatabaseDownError

    monkeypatch.setattr(db_session, "commit", failing_commit)
    with pytest.raises(_DatabaseDownError):
        await post_exchange(client)
    monkeypatch.setattr(db_session, "commit", real_commit)

    retried = await post_exchange(client)

    assert retried.json()["status"] == "criado"
    assert len(await _conversations(db_session)) == 1
    assert len(await _messages(db_session)) == 2


@pytest.mark.asyncio
async def test_ingest_marks_the_conversation_as_active_even_when_nothing_else_changes(
    client, db_session
):
    await post_exchange(client, whatsapp_message_id="wamid.a")
    (conversation,) = await _conversations(db_session)
    stale = conversation.updated_at.replace(year=2020)
    conversation.updated_at = stale
    await db_session.commit()

    await post_exchange(client, whatsapp_message_id="wamid.b")

    await db_session.refresh(conversation)
    assert conversation.updated_at.replace(tzinfo=None) > stale.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_ingest_stores_markup_verbatim_and_returns_it_as_json(client, db_session):
    markup = '<img src=x onerror="alert(1)"> <script>alert(2)</script>'

    response = await post_exchange(client, texto=markup, resposta=markup)

    assert response.headers["content-type"].startswith("application/json")
    stored = await db_session.execute(select(func.count()).where(Message.conteudo == markup))
    assert stored.scalar_one() == 2
    assert set(response.json()) == {"status", "conversa_id"}
