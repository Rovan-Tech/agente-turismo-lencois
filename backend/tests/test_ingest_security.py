"""Mitigações do threat model `2026-10-01-ingestao-de-atendimentos-do-n8n.md`, uma por teste."""

import json
import logging
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.services import message_handler
from tests.conftest import TEST_DASHBOARD_TOKEN
from tests.ingest_support import (
    INGEST_BEARER,
    INGEST_URL,
    app_log_text,
    ingest_headers,
    post_exchange,
    valid_payload,
)

pytestmark = pytest.mark.usefixtures("ingest_token")

MAX_BODY_BYTES = 16 * 1024

INVALID_CREDENTIALS = {
    "no_token": {"Authorization": ""},
    "wrong_token": ingest_headers("token-errado"),
    "basic_scheme": {"Authorization": f"Basic {INGEST_BEARER}"},
    "bearer_without_value": {"Authorization": "Bearer"},
    "no_scheme": {"Authorization": INGEST_BEARER},
    "lowercase_scheme": {"Authorization": f"bearer {INGEST_BEARER}"},
    "dashboard_token": ingest_headers(TEST_DASHBOARD_TOKEN),
}


async def _conversation_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Conversation.id)))
    return int(result.scalar_one())


# --- Spoofing: quem pode escrever -------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", INVALID_CREDENTIALS.values(), ids=INVALID_CREDENTIALS.keys())
async def test_ingest_rejects_invalid_credentials_without_writing(client, db_session, headers):
    response = await post_exchange(client, headers=headers)

    assert response.status_code == 401
    assert await _conversation_count(db_session) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("bearer", ["Bearer ", "Bearer anything"])
async def test_ingest_with_unset_token_returns_401_even_for_empty_bearer(
    client, monkeypatch, bearer
):
    monkeypatch.setattr(get_settings(), "ingest_api_token", "")

    response = await post_exchange(client, headers={"Authorization": bearer})

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/api/conversations", "/api/tours"])
async def test_ingest_token_is_rejected_by_dashboard_routes(client, route):
    response = await client.get(route, headers=ingest_headers())

    assert response.status_code == 401


UNAUTHENTICATED_REQUESTS = {
    "token_in_query_string": {
        "url": f"{INGEST_URL}?token={INGEST_BEARER}",
        "json": valid_payload(),
        "headers": {"Authorization": ""},
    },
    "auth_runs_before_body_validation": {
        "url": INGEST_URL,
        "content": b"nem e json",
        "headers": {"Authorization": "Bearer errado"},
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_kwargs", UNAUTHENTICATED_REQUESTS.values(), ids=UNAUTHENTICATED_REQUESTS.keys()
)
async def test_ingest_returns_401_before_reading_the_body_or_the_query(client, request_kwargs):
    response = await client.post(**request_kwargs)

    assert response.status_code == 401


NON_ASCII_BEARER = "Bearer é".encode()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "url"),
    [("POST", INGEST_URL), ("GET", "/api/conversations"), ("GET", "/api/tours")],
    ids=["ingest", "conversations", "tours"],
)
async def test_non_ascii_authorization_returns_401_instead_of_crashing(client, method, url):
    response = await client.request(method, url, headers={"Authorization": NON_ASCII_BEARER})

    assert response.status_code == 401


# --- Tampering: formato e tamanho do que chega ------------------------------------------------

INVALID_PAYLOADS = {
    "unknown_field": {"status": "resolvida"},
    "phone_with_plus": {"telefone": "+5598900000001"},
    "phone_with_space": {"telefone": "55 98900000001"},
    "phone_letters": {"telefone": "abc"},
    "phone_too_short": {"telefone": "123"},
    "phone_too_long": {"telefone": "9" * 16},
    "phone_empty": {"telefone": ""},
    "phone_int": {"telefone": 5598900000001},
    "texto_int": {"texto": 123},
    "resposta_list": {"resposta": ["x"]},
    "idioma_int": {"idioma": 1},
    "idioma_unsupported": {"idioma": "fr"},
    "idioma_uppercase": {"idioma": "PT"},
    "idioma_empty": {"idioma": ""},
    "tour_int": {"passeio_sugerido_id": 7},
    "flag_string": {"precisa_atencao_humana": "true"},
    "flag_int": {"precisa_atencao_humana": 1},
    "flag_null": {"precisa_atencao_humana": None},
    "id_int": {"whatsapp_message_id": 99},
    "texto_too_long": {"texto": "a" * 4097},
    "resposta_too_long": {"resposta": "a" * 4097},
    "texto_empty": {"texto": ""},
    "resposta_blank": {"resposta": "   "},
    "id_too_long": {"whatsapp_message_id": "w" * 129},
    "id_empty": {"whatsapp_message_id": ""},
    "tour_too_long": {"passeio_sugerido_id": "p" * 129},
    "texto_with_nul": {"texto": "oi\u0000"},
    "resposta_with_nul": {"resposta": "ok\u0000"},
    "id_with_nul": {"whatsapp_message_id": "wamid\u0000x"},
    "tour_with_nul": {"passeio_sugerido_id": "rio\u0000"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("override", INVALID_PAYLOADS.values(), ids=INVALID_PAYLOADS.keys())
async def test_ingest_rejects_invalid_payloads_without_writing(client, db_session, override):
    response = await post_exchange(client, **override)

    assert response.status_code == 422
    assert await _conversation_count(db_session) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field", list(valid_payload()))
async def test_ingest_rejects_a_payload_missing_any_field(client, field):
    payload = valid_payload()
    del payload[field]

    response = await client.post(INGEST_URL, json=payload, headers=ingest_headers())

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_accepts_the_largest_valid_fields(client):
    response = await post_exchange(
        client, texto="a" * 4096, resposta="b" * 4096, whatsapp_message_id="w" * 128
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "status"),
    [
        (b"isto nao e json {", 422),
        (json.dumps(valid_payload(texto="a" * (MAX_BODY_BYTES + 1))).encode(), 413),
    ],
    ids=["malformed_json", "body_over_16_kib"],
)
async def test_ingest_rejects_unreadable_bodies_without_writing(client, db_session, body, status):
    response = await client.post(
        INGEST_URL, content=body, headers=ingest_headers() | {"Content-Type": "application/json"}
    )

    assert response.status_code == status
    assert await _conversation_count(db_session) == 0


def _padded_body(size: int) -> bytes:
    """JSON válido com exatamente `size` bytes (espaços no fim), para testar o teto do corpo."""
    raw = json.dumps(valid_payload()).encode()
    return raw + b" " * (size - len(raw))


async def _as_chunks(body: bytes) -> AsyncIterator[bytes]:
    """Entrega o corpo em pedaços, sem `Content-Length` (Transfer-Encoding: chunked)."""
    yield body[: len(body) // 2]
    yield body[len(body) // 2 :]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("size", "streamed", "status"),
    [
        (MAX_BODY_BYTES, False, 200),
        (MAX_BODY_BYTES, True, 200),
        (MAX_BODY_BYTES + 1, False, 413),
        (MAX_BODY_BYTES + 1, True, 413),
    ],
    ids=["limit_with_length", "limit_chunked", "over_with_length", "over_chunked"],
)
async def test_ingest_body_limit_holds_at_the_boundary_with_and_without_content_length(
    client, size, streamed, status
):
    body = _padded_body(size)

    response = await client.post(
        INGEST_URL,
        content=_as_chunks(body) if streamed else body,
        headers=ingest_headers() | {"Content-Type": "application/json"},
    )

    assert response.status_code == status


# --- Information disclosure: o que sai na resposta e nos logs ---------------------------------


@pytest.mark.asyncio
async def test_ingest_validation_error_does_not_echo_submitted_values(client):
    personal_text = "texto-pessoal-que-nao-pode-voltar"

    response = await post_exchange(
        client, telefone="12345", texto=personal_text, extra=personal_text
    )

    assert response.status_code == 422
    assert personal_text not in response.text
    assert "12345" not in response.text
    assert '"input"' not in response.text


PERSONAL = {
    "telefone": "5598977770001",
    "texto": "frase-unica-do-turista",
    "resposta": "resposta-unica-do-bot",
    "whatsapp_message_id": "wamid.unico-da-meta",
}


@pytest.mark.asyncio
async def test_ingest_never_logs_phone_text_or_token(client, caplog):
    caplog.set_level(logging.DEBUG)
    payload = valid_payload(**PERSONAL)

    await client.post(INGEST_URL, json=payload, headers=ingest_headers())
    await client.post(INGEST_URL, json=payload, headers=ingest_headers())
    await client.post(INGEST_URL, json=payload | {"telefone": "x"}, headers=ingest_headers())
    await client.post(INGEST_URL, json=payload, headers=ingest_headers("token-errado"))

    logged = app_log_text(caplog)
    assert all(value not in logged for value in [*PERSONAL.values(), INGEST_BEARER])


@pytest.mark.asyncio
async def test_ingest_unreachable_database_returns_503(client, monkeypatch):
    """Banco fora do ar sobe do asyncpg como `OSError`, não como `SQLAlchemyError`."""

    async def refusing_store(*args: object, **kwargs: object) -> bool:
        raise ConnectionRefusedError

    monkeypatch.setattr(message_handler, "store_incoming", refusing_store)

    response = await post_exchange(client)

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ingest_database_failure_returns_503_without_logging_personal_data(
    client, caplog, monkeypatch
):
    """O texto da exceção do SQLAlchemy traz os parâmetros do SQL (telefone e texto do turista)."""
    caplog.set_level(logging.DEBUG)
    leaked = f"INSERT INTO messages ... {PERSONAL}"

    async def failing_store(*args: object, **kwargs: object) -> bool:
        raise OperationalError(leaked, PERSONAL, ConnectionError("connection is closed"))

    monkeypatch.setattr(message_handler, "store_incoming", failing_store)

    response = await client.post(
        INGEST_URL, json=valid_payload(**PERSONAL), headers=ingest_headers()
    )

    assert response.status_code == 503
    assert all(value not in response.text for value in PERSONAL.values())
    logged = app_log_text(caplog, loggers=("app", "sqlalchemy", "uvicorn"))
    assert all(value not in logged for value in PERSONAL.values())
    assert "OperationalError" in logged


@pytest.mark.asyncio
async def test_ingest_logs_the_outcome_without_personal_data(client, caplog):
    caplog.set_level(logging.INFO, logger="app")

    await post_exchange(client)
    await post_exchange(client)

    logged = app_log_text(caplog)
    assert "criado" in logged
    assert "duplicado" in logged
