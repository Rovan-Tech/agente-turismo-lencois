"""Login do painel: modos de transição, CSRF, logs, CORS e separação das credenciais (ADR-0006)."""

import logging

import httpx
import pytest

from app.api import deps
from app.core.config import get_settings
from tests.access_support import (
    AUDIENCE,
    NO_BEARER,
    PANEL_URL,
    get_panel,
    jwt_header,
)
from tests.conftest import TEST_DASHBOARD_TOKEN, persist
from tests.ingest_support import INGEST_URL, app_log_text, valid_payload

# --- Modos de transição: token -> both -> access ---------------------------------------------


@pytest.mark.asyncio
async def test_panel_auth_mode_token_ignores_the_access_jwt(client, access, monkeypatch):
    monkeypatch.setattr(get_settings(), "panel_auth_mode", "token")

    assert (await get_panel(client, access.token())).status_code == 401
    assert (await client.get(PANEL_URL)).status_code == 200


@pytest.mark.asyncio
async def test_panel_auth_mode_both_accepts_the_static_token_or_the_jwt(
    client, access, monkeypatch
):
    monkeypatch.setattr(get_settings(), "panel_auth_mode", "both")

    assert (await client.get(PANEL_URL)).status_code == 200
    assert (await get_panel(client, access.token())).status_code == 200
    assert (await client.get(PANEL_URL, headers=NO_BEARER)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_mode_access_rejects_the_static_token(client, access):
    bearer = {"Authorization": f"Bearer {TEST_DASHBOARD_TOKEN}"}

    assert (await client.get(PANEL_URL, headers=bearer)).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "bearer_status"), [("access", 401), ("both", 200)], ids=["access", "both"]
)
async def test_panel_auth_without_access_settings_rejects_every_jwt(
    client, access, monkeypatch, mode, bearer_status
):
    token = access.token()
    monkeypatch.setattr(get_settings(), "panel_auth_mode", mode)
    monkeypatch.setattr(get_settings(), "access_aud", "")

    assert (await get_panel(client, token)).status_code == 401
    assert (await client.get(PANEL_URL)).status_code == bearer_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("team_domain", "audience"),
    [
        ("", AUDIENCE),
        ("https://equipe.cloudflareaccess.com", ""),
        ("", ""),
    ],
    ids=["no_team_domain", "no_audience", "neither"],
)
async def test_panel_auth_incomplete_access_settings_never_reach_the_validation(
    client, access, monkeypatch, team_domain, audience
):
    calls: list[str] = []

    async def spy(*args: object) -> None:
        calls.append("chamado")

    monkeypatch.setattr(deps, "verify_access_jwt", spy)
    monkeypatch.setattr(get_settings(), "access_team_domain", team_domain)
    monkeypatch.setattr(get_settings(), "access_aud", audience)

    assert (await get_panel(client, access.token())).status_code == 401
    assert calls == []


# --- CSRF: a sessão por cookie exige um cabeçalho que outra página não consegue enviar ---------

PANEL_MUTATIONS = {
    "patch_conversation_status": ("PATCH", "/api/conversations/x/status"),
    "post_tour": ("POST", "/api/tours"),
    "put_tour": ("PUT", "/api/tours/x"),
    "delete_tour": ("DELETE", "/api/tours/x"),
    "post_booking": ("POST", "/api/tours/x/agendamentos"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("method_and_url", PANEL_MUTATIONS.values(), ids=PANEL_MUTATIONS.keys())
@pytest.mark.parametrize("header_value", [None, "", "0", "true", "11"], ids=str)
async def test_panel_auth_mutation_without_the_exact_panel_header_is_rejected(
    client, access, method_and_url, header_value
):
    method, url = method_and_url
    headers = jwt_header(access.token())
    if header_value is not None:
        headers["X-Panel-Request"] = header_value

    response = await client.request(method, url, headers=headers, json={})

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("method_and_url", PANEL_MUTATIONS.values(), ids=PANEL_MUTATIONS.keys())
async def test_panel_auth_mutation_with_panel_header_reaches_the_route(
    client, access, method_and_url
):
    method, url = method_and_url
    headers = jwt_header(access.token()) | {"X-Panel-Request": "1"}

    response = await client.request(method, url, headers=headers, json={})

    assert response.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_panel_auth_static_token_mutation_does_not_need_the_panel_header(
    client, access, monkeypatch
):
    """O token fixo vai num cabeçalho explícito, não é enviado sozinho pelo navegador."""
    monkeypatch.setattr(get_settings(), "panel_auth_mode", "both")

    assert (await client.delete("/api/tours/x")).status_code == 404


# --- Repúdio e vazamento: quem agiu fica no log, o JWT e o e-mail não ------------------------


@pytest.mark.asyncio
async def test_panel_auth_mutation_logs_the_actor_sub_without_email_or_jwt(client, access, caplog):
    caplog.set_level(logging.INFO, logger="app")
    token = access.token()

    await client.delete("/api/tours/x", headers=jwt_header(token) | {"X-Panel-Request": "1"})

    logged = app_log_text(caplog)
    assert "pessoa-123" in logged
    assert "pessoa@exemplo.com" not in logged
    assert token not in logged


BOOKING_PAYLOAD = {"data": "2026-09-28", "pessoas": 2, "forma_pagamento": "pix"}


def _booking_audit_actor(caplog: pytest.LogCaptureFixture) -> object:
    (record,) = [r for r in caplog.records if getattr(r, "event", None) == "booking_created"]
    return getattr(record, "ator", None)


@pytest.mark.asyncio
async def test_booking_audit_log_records_the_person_from_the_access_jwt(
    client, db_session, sample_tours, access, caplog
):
    await persist(db_session, sample_tours[0])
    caplog.set_level(logging.INFO, logger="app")
    headers = jwt_header(access.token()) | {"X-Panel-Request": "1"}

    response = await client.post(
        "/api/tours/passeio-bugre-orla/agendamentos", json=BOOKING_PAYLOAD, headers=headers
    )

    assert response.status_code == 201
    assert _booking_audit_actor(caplog) == "pessoa-123"


@pytest.mark.asyncio
async def test_booking_audit_log_falls_back_to_dashboard_with_the_static_token(
    client, db_session, sample_tours, caplog
):
    await persist(db_session, sample_tours[0])
    caplog.set_level(logging.INFO, logger="app")

    response = await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=BOOKING_PAYLOAD)

    assert response.status_code == 201
    assert _booking_audit_actor(caplog) == "dashboard"


@pytest.mark.asyncio
async def test_panel_auth_never_logs_the_jwt_or_email(client, access, caplog):
    caplog.set_level(logging.DEBUG)
    token = access.token()

    await get_panel(client, token)
    await get_panel(client, access.token(exp=1))

    logged = app_log_text(caplog, loggers=("app", "uvicorn"))
    assert token not in logged
    assert "pessoa@exemplo.com" not in logged


# --- Elevação: as credenciais do painel e do n8n não se misturam -----------------------------


@pytest.mark.asyncio
async def test_ingest_rejects_the_panel_jwt(client, access, ingest_token):
    headers = jwt_header(access.token())

    response = await client.post(INGEST_URL, json=valid_payload(), headers=headers)

    assert response.status_code == 401


# --- CORS: o modo `access` fecha as origens de navegador na própria aplicação ---------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(("mode", "allowed"), [("token", True), ("both", True), ("access", False)])
async def test_app_cors_follows_the_panel_auth_mode(mode, allowed):
    from app.core.config import Settings
    from app.main import create_app

    origin = "https://painel.exemplo.com"
    app = create_app(Settings.model_validate({"panel_auth_mode": mode, "frontend_origin": origin}))
    transport = httpx.ASGITransport(app=app)
    preflight = {"Origin": origin, "Access-Control-Request-Method": "GET"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as browser:
        response = await browser.options(PANEL_URL, headers=preflight)

    assert ("access-control-allow-origin" in response.headers) is allowed
