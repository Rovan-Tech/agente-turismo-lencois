"""Nome do perfil do WhatsApp do turista: guarda, atualiza, expõe ao painel e não vaza (LGPD).

Chega por dois caminhos: o fluxo do n8n (`cliente_nome` no contrato de ingestão, opcional) e o
webhook antigo da Meta (`contacts[].profile.name`). Em ambos o nome é dado pessoal: só vai ao banco
e ao painel, nunca a log, a mensagem de erro, ao prompt do LLM nem a resposta do n8n.
"""

import logging
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.conversation import Conversation
from app.models.message import MessageType
from app.services import message_handler, whatsapp_client
from app.services.customer_name import MAX_LENGTH, clean_profile_name
from app.services.groq_client import GroqReply
from tests import ingest_support as support

pytestmark = pytest.mark.usefixtures("ingest_token")

NAME = "Mariana Souza Unica"
INBOUND_URL = "/api/ingest/mensagens"


async def _stored_name(db_session: AsyncSession) -> str | None:
    conversation = (await db_session.execute(select(Conversation))).scalars().one()
    await db_session.refresh(conversation)
    name: str | None = conversation.cliente_nome
    return name


async def _post_inbound(client: AsyncClient, **overrides: object) -> Response:
    payload = {
        "whatsapp_message_id": "wamid.entrada-1",
        "telefone": "5598900000001",
        "texto": "oi",
        "idioma": None,
    }
    return await client.post(
        INBOUND_URL, json=payload | overrides, headers=support.ingest_headers()
    )


async def _post_webhook(client: AsyncClient, **kwargs: Any) -> Response:
    return await client.post("/webhook/whatsapp", json=_webhook_payload(**kwargs))


# --- Limpeza -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Mariana Souza", "Mariana Souza"),
        ("  Mariana \n\t Souza  ", "Mariana Souza"),
        ("Ma\u0000ri\u0007ana", "Mariana"),
        ("Zoë 🌴", "Zoë 🌴"),
        ("x" * (MAX_LENGTH + 20), "x" * MAX_LENGTH),
        ("a" * (MAX_LENGTH - 1) + " b", "a" * (MAX_LENGTH - 1)),
        ("", None),
        ("   \n ", None),
        ("\u0000\u0001", None),
        (None, None),
        (42, None),
        (["Mariana"], None),
    ],
    ids=[
        "plain",
        "collapses_whitespace",
        "drops_control_chars",
        "keeps_unicode_and_emoji",
        "truncates",
        "truncation_leaves_no_trailing_space",
        "empty",
        "blank",
        "only_control_chars",
        "none",
        "number",
        "list",
    ],
)
def test_clean_profile_name(raw, expected):
    assert clean_profile_name(raw) == expected


# --- Ingestão (n8n) ----------------------------------------------------------------------------


async def test_ingest_stores_the_name_and_the_panel_api_shows_it(client, db_session):
    response = await support.post_exchange(client, cliente_nome=NAME)

    assert response.status_code == 200
    assert await _stored_name(db_session) == NAME
    [summary] = (await client.get("/api/conversations")).json()
    assert summary["cliente_nome"] == NAME
    detail = (await client.get(f"/api/conversations/{response.json()['conversa_id']}")).json()
    assert detail["cliente_nome"] == NAME
    assert detail["whatsapp_phone"] == "5598900000001"


async def test_ingest_without_the_field_still_works_and_the_name_is_null(client, db_session):
    """Retrocompatível: o fluxo do n8n sem o campo novo continua sendo aceito."""
    assert "cliente_nome" not in support.valid_payload()

    response = await support.post_exchange(client)

    assert response.status_code == 200
    assert await _stored_name(db_session) is None
    [summary] = (await client.get("/api/conversations")).json()
    assert summary["cliente_nome"] is None


@pytest.mark.parametrize("absent", [{}, {"cliente_nome": None}, {"cliente_nome": "  "}])
async def test_a_later_message_without_a_name_keeps_the_stored_one(client, db_session, absent):
    await support.post_exchange(client, whatsapp_message_id="wamid.a", cliente_nome=NAME)

    await support.post_exchange(client, whatsapp_message_id="wamid.b", **absent)

    assert await _stored_name(db_session) == NAME


async def test_a_different_name_replaces_the_stored_one(client, db_session):
    """O turista pode trocar o nome do perfil: vale o mais recente."""
    await support.post_exchange(client, whatsapp_message_id="wamid.a", cliente_nome=NAME)

    await support.post_exchange(client, whatsapp_message_id="wamid.b", cliente_nome="Nome Novo")

    assert await _stored_name(db_session) == "Nome Novo"


async def test_the_name_is_cleaned_before_it_is_stored(client, db_session):
    await support.post_exchange(client, cliente_nome=f"  {NAME}\n\t ")

    assert await _stored_name(db_session) == NAME


async def test_a_repeated_delivery_does_not_change_the_name(client, db_session):
    await support.post_exchange(client, cliente_nome=NAME)

    again = await support.post_exchange(client, cliente_nome="Outro Nome")

    assert again.json()["status"] == "duplicado"
    assert await _stored_name(db_session) == NAME


async def test_the_message_only_route_stores_the_name_too(client, db_session):
    """Com uma pessoa atendendo o n8n só registra a mensagem; o nome também vale aí."""
    response = await _post_inbound(client, cliente_nome=NAME)

    assert response.status_code == 200
    assert await _stored_name(db_session) == NAME


async def test_the_message_only_route_without_the_field_is_still_accepted(client, db_session):
    response = await _post_inbound(client)

    assert response.status_code == 200
    assert await _stored_name(db_session) is None


@pytest.mark.parametrize(
    "bad",
    [123, ["Mariana"], "a" * (MAX_LENGTH + 1), "Mari\u0000ana"],
    ids=["number", "list", "too_long", "nul"],
)
async def test_ingest_rejects_an_invalid_name_without_echoing_it(client, db_session, bad):
    response = await support.post_exchange(client, cliente_nome=bad)

    assert response.status_code == 422
    assert "Mariana" not in response.text
    assert "aaaa" not in response.text
    assert (await db_session.execute(select(Conversation))).first() is None


def test_openapi_documents_the_optional_name_in_the_ingest_request_bodies():
    paths = app.openapi()["paths"]

    for path in ("/api/ingest/atendimentos", "/api/ingest/mensagens"):
        schema = paths[path]["post"]["requestBody"]["content"]["application/json"]["schema"]
        name = schema["properties"]["cliente_nome"]
        assert "cliente_nome" not in schema["required"]
        assert {"type": "null"} in name["anyOf"]
        assert name["description"]


# --- Webhook antigo da Meta --------------------------------------------------------------------


def _webhook_payload(
    phone: str = "5598999990001", contacts: object = None, **message: object
) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "from": phone,
        "id": "wamid.antigo-1",
        "type": "text",
        "text": {"body": "oi"},
    }
    value: dict[str, Any] = {"messages": [msg | message]}
    if contacts is not None:
        value["contacts"] = contacts
    return {"entry": [{"changes": [{"value": value}]}]}


def _contact(wa_id: str, name: object) -> dict[str, object]:
    return {"wa_id": wa_id, "profile": {"name": name}}


async def test_webhook_stores_the_profile_name_of_the_sender(client, db_session, pipeline_spies):
    contacts = [_contact("5598000000000", "Outra Pessoa"), _contact("5598999990001", NAME)]

    response = await _post_webhook(client, contacts=contacts)

    assert response.status_code == 200
    assert await _stored_name(db_session) == NAME


@pytest.mark.parametrize(
    "contacts",
    [
        None,
        [],
        [_contact("5598000000000", "Outra Pessoa")],
        [{"wa_id": "5598999990001"}],
        [{"wa_id": "5598999990001", "profile": "texto"}],
        [_contact("5598999990001", 42)],
        [_contact("5598999990001", "  ")],
        ["lixo", None, {"profile": {"name": NAME}}],
    ],
    ids=[
        "no_contacts",
        "empty",
        "other_sender",
        "no_profile",
        "profile_not_object",
        "name_not_text",
        "blank_name",
        "malformed_contacts",
    ],
)
async def test_webhook_without_a_usable_name_leaves_it_empty(
    client, db_session, pipeline_spies, contacts
):
    response = await _post_webhook(client, contacts=contacts)

    assert response.status_code == 200
    assert await _stored_name(db_session) is None


async def test_webhook_audio_message_also_stores_the_name(
    client, db_session, pipeline_spies, monkeypatch
):
    async def fake_resolve(settings, message_type, text_body, media_id):
        return "transcrito", MessageType.AUDIO_TRANSCRITO

    monkeypatch.setattr(message_handler, "resolve_incoming_text", fake_resolve)
    contacts = [_contact("5598999990001", NAME)]

    response = await _post_webhook(client, contacts=contacts, type="audio", audio={"id": "media-1"})

    assert response.status_code == 200
    assert await _stored_name(db_session) == NAME


async def test_a_later_webhook_message_without_contacts_keeps_the_name(
    client, db_session, pipeline_spies
):
    contacts = [_contact("5598999990001", NAME)]
    await _post_webhook(client, contacts=contacts)

    await _post_webhook(client, id="wamid.antigo-2", text={"body": "e aí?"})

    assert await _stored_name(db_session) == NAME


# --- LGPD: o nome não vaza ---------------------------------------------------------------------


async def test_the_name_never_reaches_the_llm_prompt_or_the_tourist_reply(
    client, db_session, sample_tours, monkeypatch
):
    seen: list[str] = []
    sent: list[str] = []

    async def fake_ask_groq(settings, system_prompt, user_message):
        seen.extend([system_prompt, user_message])
        return GroqReply(idioma="pt", precisa_atencao_humana=False, resposta="ok")

    async def fake_send(settings, to, body):
        sent.append(body)

    monkeypatch.setattr(message_handler, "ask_groq", fake_ask_groq)
    monkeypatch.setattr(whatsapp_client, "send_text_message", fake_send)
    for tour in sample_tours:
        db_session.add(tour)
    await db_session.commit()
    contacts = [_contact("5598999990001", NAME)]

    await _post_webhook(client, contacts=contacts)

    assert seen
    assert all(NAME not in text for text in [*seen, *sent])
    assert await _stored_name(db_session) == NAME


async def test_the_name_is_never_logged_by_the_ingest_routes(client, caplog):
    caplog.set_level(logging.DEBUG)

    await support.post_exchange(client, cliente_nome=NAME)  # criado
    await support.post_exchange(client, cliente_nome=NAME)  # duplicado
    await support.post_exchange(client, cliente_nome=NAME, telefone="x")  # 422
    await _post_inbound(client, cliente_nome=NAME)

    logged = support.app_log_text(caplog)
    assert logged
    assert NAME not in logged


async def test_a_database_failure_does_not_log_or_return_the_name(client, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    leaked = f"falha ao gravar o perfil {NAME}"

    async def failing_store(*args: object, **kwargs: object) -> bool:
        raise OperationalError(leaked, {}, OSError("connection is closed"))

    monkeypatch.setattr(message_handler, "store_incoming", failing_store)

    response = await client.post(
        support.INGEST_URL,
        json=support.valid_payload(cliente_nome=NAME),
        headers=support.ingest_headers(),
    )

    assert response.status_code == 503
    assert NAME not in response.text
    assert NAME not in support.app_log_text(caplog, loggers=("app", "sqlalchemy", "uvicorn"))


async def test_the_name_is_never_logged_by_the_webhook(client, caplog, pipeline_spies):
    caplog.set_level(logging.DEBUG)
    contacts = [_contact("5598999990001", NAME)]

    await _post_webhook(client, contacts=contacts)

    assert NAME not in support.app_log_text(caplog)
