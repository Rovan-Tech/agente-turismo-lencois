"""Atendimento humano: responder pelo painel, devolução à IA e a consulta do n8n (ADR-0008)."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.conversations import locked_conversation_query
from app.core.config import get_settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageAuthor
from app.services import handoff, message_handler
from tests.access_support import AccessEnv, panel_headers
from tests.handoff_support import (
    PHONE,
    act,
    assert_refused,
    holding,
    meta_rejection,
)
from tests.ingest_support import app_log_text, ingest_headers

pytestmark = pytest.mark.asyncio

STATE_URL = "/api/ingest/conversas/atendimento"
INBOUND_URL = "/api/ingest/mensagens"


async def _send(
    client: httpx.AsyncClient,
    access: AccessEnv,
    conversation: Conversation,
    text: str = "Claro, posso ajudar!",
    client_message_id: str = "envio-0001",
    token: str = "",
) -> httpx.Response:
    body: dict[str, object] = {"texto": text, "client_message_id": client_message_id}
    return await act(
        client, conversation, "mensagens", panel_headers(token or access.token()), body
    )


async def _count(db: AsyncSession, *conditions: ColumnElement[bool]) -> int:
    result = await db.execute(select(func.count()).select_from(Message).where(*conditions))
    return int(result.scalar_one())


# --- Responder pelo painel -----------------------------------------------------------------------


async def test_send_goes_to_the_phone_of_the_conversation_and_records_the_author(
    client, db_session, access, held, outbox
):
    response = await _send(client, access, held)

    assert response.status_code == 200
    assert outbox.sent == [(PHONE, "Claro, posso ajudar!")]
    saved = (
        await db_session.execute(select(Message).where(Message.client_message_id == "envio-0001"))
    ).scalar_one()
    assert (saved.autor, saved.autor_sub, saved.conversation_id) == (
        MessageAuthor.ATENDENTE,
        "pessoa-123",
        held.id,
    )


async def test_send_is_idempotent_by_client_message_id(client, access, held, outbox):
    first = await _send(client, access, held)
    second = await _send(client, access, held)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(outbox.sent) == 1


async def test_send_concurrent_same_client_message_id_sends_once(
    client, db_session, access, held, outbox, monkeypatch
):
    """Dois cliques em paralelo: a checagem inicial não vê o primeiro, mas o índice único barra."""
    await _send(client, access, held)

    async def blind(db: AsyncSession, client_message_id: str) -> None:
        return None

    monkeypatch.setattr(handoff, "find_by_client_message_id", blind)
    second = await _send(client, access, held)

    assert second.status_code == 200
    assert len(outbox.sent) == 1
    assert await _count(db_session, Message.client_message_id == "envio-0001") == 1


async def test_send_requires_the_conversation_to_be_in_human_mode(
    client, access, conversation, outbox
):
    response = await _send(client, access, conversation)

    assert_refused(response, outbox)


async def test_send_by_someone_who_is_not_the_holder_is_409(client, access, held, outbox):
    response = await _send(client, access, held, token=access.token(sub="outra-pessoa"))

    assert response.status_code == 409
    assert "Pessoa" in response.json()["detail"]
    assert outbox.sent == []


async def test_send_outside_the_24h_window_is_409(client, db_session, access, outbox):
    conversation = await holding(db_session, tourist_minutes_ago=24 * 60 + 5)

    response = await _send(client, access, conversation)

    assert response.status_code == 409
    assert "24 horas" in response.json()["detail"]
    assert outbox.sent == []


async def test_send_meta_failure_does_not_save_the_message_or_echo_the_provider_error(
    client, db_session, access, held, outbox
):
    outbox.failure = meta_rejection(131056)

    response = await _send(client, access, held)

    assert response.status_code == 502
    assert "131056" in response.json()["detail"]
    assert "detalhe-interno-da-meta" not in response.text
    assert await _count(db_session, Message.autor == MessageAuthor.ATENDENTE) == 0


async def test_send_is_capped_per_conversation_per_hour(client, access, held, outbox, monkeypatch):
    monkeypatch.setattr(get_settings(), "human_send_cap_per_hour", 2)

    first = await _send(client, access, held, client_message_id="envio-0001")
    second = await _send(client, access, held, client_message_id="envio-0002")
    third = await _send(client, access, held, client_message_id="envio-0003")

    assert [r.status_code for r in (first, second, third)] == [200, 200, 429]
    assert len(outbox.sent) == 2


async def test_send_stores_markup_verbatim(client, access, held, outbox):
    markup = '<img src=x onerror="alert(1)">'

    response = await _send(client, access, held, text=markup)

    assert response.json()["conteudo"] == markup
    assert outbox.sent[0][1] == markup


# --- Devolução automática para a IA ----------------------------------------------------------


@pytest.mark.parametrize(("hours_ago", "expected"), [(1.9, "humano"), (2.1, "ia")])
async def test_state_returns_to_ia_after_the_idle_hours(
    client, db_session, access, outbox, hours_ago, expected
):
    await holding(db_session, hours_ago=hours_ago)

    summary = (
        await client.get("/api/conversations", headers=panel_headers(access.token()))
    ).json()[0]

    assert summary["atendimento"] == expected
    assert (summary["atendente_nome"] is None) == (expected == "ia")


@pytest.mark.parametrize(
    ("hours_ago", "status"),
    [(3, ConversationStatus.ABERTA), (0.1, ConversationStatus.RESOLVIDA)],
    ids=["idle_return_to_ia", "resolved"],
)
async def test_send_to_a_conversation_the_attendant_no_longer_holds_is_refused(
    client, db_session, access, outbox, hours_ago, status
):
    conversation = await holding(db_session, hours_ago=hours_ago, status=status)

    response = await _send(client, access, conversation)

    assert_refused(response, outbox)


async def test_a_message_from_the_attendant_renews_the_activity(client, db_session, access, outbox):
    conversation = await holding(db_session, hours_ago=1.5)

    await _send(client, access, conversation)

    await db_session.refresh(conversation)
    renewed = conversation.humano_atividade_em
    assert renewed is not None
    assert datetime.now(UTC) - renewed.replace(tzinfo=UTC) < timedelta(minutes=1)


# --- A consulta do n8n ---------------------------------------------------------------------------


async def _ask_state(client: httpx.AsyncClient, phone: object) -> httpx.Response:
    return await client.post(STATE_URL, json={"telefone": phone}, headers=ingest_headers())


@pytest.mark.usefixtures("ingest_token")
async def test_state_endpoint_tells_n8n_whether_a_person_is_attending(client, db_session):
    await holding(db_session)

    response = await _ask_state(client, PHONE)

    assert response.json() == {"atendimento": "humano"}


@pytest.mark.usefixtures("ingest_token")
async def test_state_endpoint_writes_nothing(client, db_session, held):
    await db_session.refresh(held)  # mesma leitura nos dois lados (o SQLite devolve datas sem fuso)
    before = (held.updated_at, held.humano_atividade_em, await _count(db_session))

    await _ask_state(client, PHONE)

    await db_session.refresh(held)
    after = (held.updated_at, held.humano_atividade_em, await _count(db_session))
    assert after == before


@pytest.mark.usefixtures("ingest_token")
async def test_state_endpoint_answers_ia_for_a_phone_without_a_conversation(client, db_session):
    await holding(db_session)

    response = await _ask_state(client, "5511000000000")

    assert (response.status_code, response.json()) == (200, {"atendimento": "ia"})


@pytest.mark.usefixtures("ingest_token")
@pytest.mark.parametrize(
    "phone", ["abc", "123", 5598912171865, None], ids=["letters", "short", "number", "null"]
)
async def test_state_endpoint_rejects_a_bad_phone_without_echoing_it(client, phone):
    response = await _ask_state(client, phone)

    assert response.status_code == 422
    assert "abc" not in response.text


@pytest.mark.usefixtures("ingest_token")
@pytest.mark.parametrize(
    ("url", "body", "module", "name"),
    [
        (STATE_URL, {"telefone": PHONE}, handoff, "handling_for_phone"),
        (
            INBOUND_URL,
            {"whatsapp_message_id": "wamid.x", "telefone": PHONE, "texto": "oi", "idioma": "pt"},
            message_handler,
            "store_incoming",
        ),
    ],
    ids=["state", "inbound"],
)
async def test_handoff_ingest_endpoints_return_503_without_personal_data_when_the_database_fails(
    client, caplog, monkeypatch, url, body, module, name
):
    caplog.set_level(logging.DEBUG)
    leaked = OperationalError(f"SELECT ... {PHONE}", {"p": PHONE}, ConnectionError("closed"))

    async def failing(*args: object, **kwargs: object) -> None:
        raise leaked

    monkeypatch.setattr(module, name, failing)

    response = await client.post(url, json=body, headers=ingest_headers())

    assert response.status_code == 503
    assert PHONE not in response.text
    assert PHONE not in app_log_text(caplog, loggers=("app", "sqlalchemy", "uvicorn"))


async def test_locked_conversation_query_asks_postgres_for_a_row_lock():
    statement = locked_conversation_query("c1").compile(dialect=postgresql.dialect())

    assert "FOR UPDATE" in str(statement)


@pytest.mark.usefixtures("ingest_token")
async def test_inbound_only_endpoint_records_the_tourist_message_without_replying(
    client, held, db_session, outbox
):
    body = {
        "whatsapp_message_id": "wamid.humano-1",
        "telefone": PHONE,
        "texto": "e o preço?",
        "idioma": "pt",
    }

    first = await client.post(INBOUND_URL, json=body, headers=ingest_headers())
    second = await client.post(INBOUND_URL, json=body, headers=ingest_headers())

    assert (first.json()["status"], second.json()["status"]) == ("criado", "duplicado")
    assert first.json()["conversa_id"] == held.id
    saved = (
        await db_session.execute(
            select(Message).where(Message.whatsapp_message_id == "wamid.humano-1")
        )
    ).scalar_one()
    assert saved.autor == MessageAuthor.TURISTA
    assert outbox.sent == []


async def test_legacy_webhook_does_not_answer_a_conversation_held_by_a_person(
    db_session, pipeline_spies
):
    from app.services.message_handler import IncomingMessage, process_incoming_message

    await holding(db_session)

    await process_incoming_message(
        db_session,
        get_settings(),
        IncomingMessage(PHONE, "text", "oi de novo", message_id="wamid.x"),
    )

    assert pipeline_spies["asked"] == []
    assert pipeline_spies["sent"] == []
    assert await _count(db_session, Message.conteudo == "oi de novo") == 1
