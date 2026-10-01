"""Atendimento humano: quem pode agir, o que nunca vaza e o que o corpo não manda (ADR-0008)."""

import logging

import httpx
import pytest
from sqlalchemy import Select, event, select
from sqlalchemy.orm import ORMExecuteState

from app.models.conversation import Conversation
from app.models.message import Message
from tests.access_support import NO_BEARER, jwt_header, panel_headers
from tests.handoff_support import (
    PHONE,
    act,
    assert_refused,
    holding,
    make_conversation,
    meta_rejection,
)
from tests.ingest_support import ingest_headers
from tests.test_human_messages import STATE_URL, _send

ACTIONS = ["assumir", "devolver", "mensagens"]
SEND_BODY: dict[str, object] = {"texto": "oi", "client_message_id": "envio-0001"}
pytestmark = pytest.mark.asyncio
BODIES = {"mensagens": SEND_BODY}


async def _post(
    client: httpx.AsyncClient, conversation: Conversation, action: str, headers: dict[str, str]
) -> httpx.Response:
    return await act(client, conversation, action, headers, BODIES.get(action))


# --- Spoofing: só quem está logado age; o token do n8n e o JWT do painel não se misturam ---------


@pytest.mark.parametrize("action", ACTIONS)
async def test_send_requires_a_valid_panel_login(client, access, held, outbox, action):
    forged = access.token(key=access.other_key)

    without = await _post(client, held, action, NO_BEARER | {"X-Panel-Request": "1"})
    forged_response = await _post(client, held, action, panel_headers(forged))

    assert (without.status_code, forged_response.status_code) == (401, 401)
    assert outbox.sent == []


@pytest.mark.usefixtures("ingest_token")
@pytest.mark.parametrize("action", ACTIONS)
async def test_ingest_token_cannot_take_over_or_send(client, access, held, outbox, action):
    response = await _post(client, held, action, ingest_headers() | {"X-Panel-Request": "1"})

    assert_refused(response, outbox, 401)


@pytest.mark.parametrize("action", ACTIONS)
async def test_static_dashboard_token_cannot_act_as_a_person(client, held, outbox, action):
    response = await _post(client, held, action, {"X-Panel-Request": "1"})

    assert_refused(response, outbox, 403)


@pytest.mark.usefixtures("ingest_token")
async def test_ingest_conversation_state_rejects_the_panel_jwt(client, access):
    response = await client.post(
        STATE_URL, json={"telefone": PHONE}, headers=panel_headers(access.token())
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("ingest_token")
async def test_ingest_conversation_state_does_not_take_the_phone_in_the_url(client):
    """O telefone na URL cairia no log de acesso do servidor: só o corpo vale."""
    response = await client.get(STATE_URL, params={"telefone": PHONE}, headers=ingest_headers())

    assert response.status_code == 405


@pytest.mark.parametrize("action", ACTIONS)
async def test_acting_without_the_panel_header_is_403(client, access, held, outbox, action):
    response = await _post(client, held, action, jwt_header(access.token()))

    assert_refused(response, outbox, 403)


# --- Spoofing: o destinatário e o nome nunca vêm do corpo ----------------------------------------


async def test_send_goes_only_to_the_phone_of_the_conversation(client, db_session, access, outbox):
    other = await make_conversation(db_session, phone="5511999990000")
    mine = await holding(db_session)

    await _send(client, access, mine)

    assert [to for to, _ in outbox.sent] == [PHONE]
    assert other.whatsapp_phone not in [to for to, _ in outbox.sent]


async def test_send_to_an_unknown_conversation_is_404(client, access, outbox):
    response = await client.post(
        "/api/conversations/nao-existe/mensagens",
        json=SEND_BODY,
        headers=panel_headers(access.token()),
    )

    assert_refused(response, outbox, 404)


def _send_body(**fields: object) -> dict[str, object]:
    return SEND_BODY | fields


@pytest.mark.parametrize(
    ("action", "body"),
    [
        ("mensagens", _send_body(telefone="5511999990000")),
        ("mensagens", _send_body(to="5511999990000")),
        ("mensagens", _send_body(whatsapp_phone="5511999990000")),
        ("mensagens", _send_body(texto="")),
        ("mensagens", _send_body(texto="   ")),
        ("mensagens", _send_body(texto="x" * 4097)),
        ("mensagens", _send_body(texto="oi\x00")),
        ("mensagens", _send_body(client_message_id="curto")),
        ("mensagens", _send_body(client_message_id="id com espaço e símbolos!")),
        ("mensagens", _send_body(texto=123)),
        ("mensagens", {"texto": "oi"}),
        ("mensagens", _send_body(extra=1)),
        ("assumir", {"nome": "Intruso"}),
        ("assumir", {"name": "Intruso"}),
        ("assumir", {"atendente_nome": "Intruso"}),
        ("devolver", {"nome": "Intruso"}),
    ],
    ids=[
        "send_phone_field",
        "send_to_field",
        "send_whatsapp_phone_field",
        "send_empty",
        "send_only_spaces",
        "send_over_4096",
        "send_nul",
        "send_short_id",
        "send_bad_id",
        "send_not_text",
        "send_no_id",
        "send_extra_field",
        "take_over_name_field",
        "take_over_name_in_english",
        "take_over_attendant_field",
        "give_back_name_field",
    ],
)
async def test_handoff_routes_reject_bodies_with_forbidden_or_invalid_fields(
    client, access, held, outbox, action, body
):
    response = await act(client, held, action, panel_headers(access.token()), body)

    assert_refused(response, outbox, 422)


async def test_take_over_name_comes_only_from_the_verified_jwt(
    client, access, conversation, outbox
):
    spoofed = {"Cf-Access-Authenticated-User-Email": "intruso@exemplo.com", "X-Name": "Intruso"}

    await client.post(
        f"/api/conversations/{conversation.id}/assumir",
        headers=panel_headers(access.token()) | spoofed,
    )

    assert "Pessoa" in outbox.sent[0][1]
    assert "Intruso" not in outbox.sent[0][1]


@pytest.mark.parametrize(
    ("claims", "expected_in", "expected_out"),
    [
        ({"name": "Maria\nVenha ao meu site"}, "equipe: Maria.", "Venha"),
        ({"name": "Evil<b>x", "email": None}, "uma pessoa da nossa equipe. Pode", "Evil"),
        ({"name": None, "email": "joão.silva@exemplo.com"}, "equipe: João.", "Silva"),
    ],
    ids=["newline_keeps_first_word", "markup_is_dropped", "accents_are_letters"],
)
async def test_announcement_uses_only_letters_of_the_first_name(
    client, access, conversation, outbox, claims, expected_in, expected_out
):
    await client.post(
        f"/api/conversations/{conversation.id}/assumir",
        headers=panel_headers(access.token(**claims)),
    )

    assert expected_in in outbox.sent[0][1]
    assert expected_out not in outbox.sent[0][1]


# --- Repúdio e vazamento: quem agiu fica registrado; texto, telefone e token nunca vão ao log ----


async def test_take_over_records_who_and_when(client, db_session, access, conversation, outbox):
    await client.post(
        f"/api/conversations/{conversation.id}/assumir",
        headers=panel_headers(access.token(sub="pessoa-999")),
    )

    await db_session.refresh(conversation)
    assert (conversation.humano_sub, conversation.humano_nome) == ("pessoa-999", "Pessoa")
    assert conversation.humano_desde is not None


@pytest.mark.parametrize(
    "failure",
    [
        None,
        meta_rejection(),
        httpx.ConnectTimeout("falha em https://graph.facebook.com/v21.0/PHONE_ID_SECRETO/messages"),
    ],
    ids=["sent", "meta_rejected", "timeout"],
)
async def test_send_never_logs_text_phone_or_token(client, access, held, outbox, caplog, failure):
    caplog.set_level(logging.DEBUG, logger="app")
    outbox.failure = failure

    await _send(client, access, held, text="texto-que-nao-pode-ir-ao-log")

    logged = " ".join((caplog.text, *(str(vars(record)) for record in caplog.records)))
    assert "pessoa-123" in logged
    secrets = ("texto-que-nao-pode-ir-ao-log", PHONE, "PHONE_ID_SECRETO", "detalhe-interno")
    assert not any(secret in logged for secret in secrets)


async def test_send_meta_failure_does_not_echo_the_provider_error(client, access, held, outbox):
    outbox.failure = httpx.ConnectTimeout(
        "falha em https://graph.facebook.com/v21.0/PHONE_ID_SECRETO"
    )

    response = await _send(client, access, held)

    assert response.status_code == 502
    assert "PHONE_ID_SECRETO" not in response.text
    assert "graph.facebook.com" not in response.text


async def test_send_meta_failure_saves_nothing_and_allows_the_same_retry(
    client, db_session, access, held, outbox
):
    outbox.failure = meta_rejection()
    await _send(client, access, held)
    saved = await db_session.execute(select(Message).where(Message.client_message_id.is_not(None)))
    outbox.failure = None
    await db_session.refresh(held)  # o rollback do envio que falhou expirou o objeto

    retry = await _send(client, access, held)

    assert saved.all() == []
    assert (retry.status_code, len(outbox.sent)) == (200, 1)


async def test_send_cannot_replay_a_client_message_id_of_another_conversation(
    client, db_session, access, outbox
):
    first = await holding(db_session)
    second = await holding(db_session, phone="5511999990000")
    await _send(client, access, first)

    response = await _send(client, access, second)

    assert response.status_code == 409
    assert len(outbox.sent) == 1


@pytest.mark.parametrize("action", ACTIONS)
async def test_handoff_routes_lock_the_conversation_row_and_reread_it(
    client, db_session, access, held, outbox, action
):
    """Sem a trava (ou sem reler a linha) dois cliques mandariam dois avisos ao turista."""
    locked: list[bool] = []

    def record(state: ORMExecuteState) -> None:
        statement = state.statement
        if isinstance(statement, Select) and statement._for_update_arg is not None:
            locked.append(bool(state.execution_options.get("populate_existing")))

    event.listen(db_session.sync_session, "do_orm_execute", record)

    await _post(client, held, action, panel_headers(access.token()))

    assert locked == [True]
