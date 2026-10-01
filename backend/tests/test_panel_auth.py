"""Login do painel com Cloudflare Access: o backend valida o JWT do Access (ADR-0006)."""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import PyJWKClientConnectionError

from app.core.config import get_settings
from tests.conftest import TEST_DASHBOARD_TOKEN
from tests.ingest_support import INGEST_URL, app_log_text, valid_payload

KID = "kid-de-teste"
AUDIENCE = "aud-do-aplicativo-de-teste"
PANEL_URL = "/api/conversations"
NO_BEARER = {"Authorization": ""}


@dataclass
class AccessEnv:
    """Equipe do Access de teste: emite JWTs e conta quantas vezes o JWKS foi buscado."""

    issuer: str
    private_key: Any
    other_key: Any
    fetches: list[int]

    def token(self, *, key: Any = None, kid: str = KID, **claims: object) -> str:
        """JWT válido por padrão; `claim=None` remove a claim."""
        now = int(time.time())
        payload: dict[str, object] = {
            "iss": self.issuer,
            "aud": [AUDIENCE],
            "sub": "pessoa-123",
            "email": "pessoa@exemplo.com",
            "iat": now,
            "exp": now + 3600,
        } | claims
        payload = {name: value for name, value in payload.items() if value is not None}
        return jwt.encode(payload, key or self.private_key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[Any, Any]:
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


def _configure(monkeypatch: pytest.MonkeyPatch, mode: str, issuer: str, audience: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "panel_auth_mode", mode)
    monkeypatch.setattr(settings, "access_team_domain", issuer)
    monkeypatch.setattr(settings, "access_aud", audience)


@pytest.fixture
def access(monkeypatch: pytest.MonkeyPatch, rsa_keys: tuple[Any, Any]) -> AccessEnv:
    """Modo `access` com um JWKS de teste (sem rede). Cada teste usa uma equipe nova: o cache é
    por endereço, então um teste não enxerga o JWKS do outro."""
    private_key, other_key = rsa_keys
    issuer = f"https://t{uuid.uuid4().hex[:10]}.cloudflareaccess.com"
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk |= {"kid": KID, "use": "sig", "alg": "RS256"}
    fetches: list[int] = []

    def fake_fetch(self: object) -> dict[str, object]:
        fetches.append(1)
        return {"keys": [jwk]}

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fake_fetch)
    _configure(monkeypatch, "access", issuer, AUDIENCE)
    return AccessEnv(issuer, private_key, other_key, fetches)


def _jwt_header(token: str) -> dict[str, str]:
    return {**NO_BEARER, "Cf-Access-Jwt-Assertion": token}


async def _get_panel(client: Any, token: str) -> Any:
    return await client.get(PANEL_URL, headers=_jwt_header(token))


def _b64(data: Mapping[str, object]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# --- Spoofing: o JWT precisa ser autêntico, atual e destinado a este aplicativo ----------------


@pytest.mark.asyncio
async def test_panel_auth_accepts_a_valid_access_jwt_on_reads_without_the_panel_header(
    client, access
):
    assert (await _get_panel(client, access.token())).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"aud": ["outra-aplicacao"]},
        {"iss": "https://outra.cloudflareaccess.com"},
        {"exp": None},
        {"sub": None},
        {"iat": None},
    ],
    ids=["expired", "wrong_audience", "wrong_issuer", "missing_exp", "missing_sub", "missing_iat"],
)
async def test_panel_auth_rejects_invalid_claims(client, access, claims):
    response = await _get_panel(client, access.token(**claims))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_a_tampered_signature(client, access):
    token = access.token()
    flipped = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    assert (await _get_panel(client, flipped)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_a_token_signed_by_another_key(client, access):
    assert (await _get_panel(client, access.token(key=access.other_key))).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_alg_none(client, access):
    now = int(time.time())
    claims = {"iss": access.issuer, "aud": [AUDIENCE], "sub": "x", "iat": now, "exp": now + 600}
    token = jwt.encode(claims, "", algorithm="none", headers={"kid": KID})

    assert (await _get_panel(client, token)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_hs256_signed_with_the_public_key(client, access):
    """Confusão de algoritmo: o atacante assina com a chave pública, que é pública."""
    public_pem = access.private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": KID}
    claims = {"iss": access.issuer, "aud": [AUDIENCE], "sub": "x", "iat": now, "exp": now + 600}
    signing_input = f"{_b64(header)}.{_b64(claims)}"
    signature = hmac.new(public_pem, signing_input.encode(), hashlib.sha256).digest()
    token = f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    assert (await _get_panel(client, token)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_unknown_kid_is_rejected(client, access):
    assert (await _get_panel(client, access.token(kid="chave-desconhecida"))).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_ignores_identity_headers_without_a_valid_jwt(client, access):
    headers = {**NO_BEARER, "Cf-Access-Authenticated-User-Email": "pessoa@exemplo.com"}

    assert (await client.get(PANEL_URL, headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_error_does_not_echo_the_token(client, access):
    token = access.token(exp=1)

    response = await _get_panel(client, token)

    assert token not in response.text


# --- Tampering e DoS: JWKS fora do ar, cache -------------------------------------------------


@pytest.mark.asyncio
async def test_panel_auth_jwks_failure_fails_closed(client, access, monkeypatch):
    def failing_fetch(self: object) -> dict[str, object]:
        raise PyJWKClientConnectionError

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", failing_fetch)

    response = await _get_panel(client, access.token())

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_panel_auth_caches_the_jwks_between_requests(client, access):
    token = access.token()

    for _ in range(3):
        await _get_panel(client, token)

    assert len(access.fetches) == 1


# --- Modos de transição: token -> both -> access ---------------------------------------------


@pytest.mark.asyncio
async def test_panel_auth_mode_token_ignores_the_access_jwt(client, access, monkeypatch):
    monkeypatch.setattr(get_settings(), "panel_auth_mode", "token")

    assert (await _get_panel(client, access.token())).status_code == 401
    assert (await client.get(PANEL_URL)).status_code == 200


@pytest.mark.asyncio
async def test_panel_auth_mode_both_accepts_the_static_token_or_the_jwt(
    client, access, monkeypatch
):
    monkeypatch.setattr(get_settings(), "panel_auth_mode", "both")

    assert (await client.get(PANEL_URL)).status_code == 200
    assert (await _get_panel(client, access.token())).status_code == 200
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

    assert (await _get_panel(client, token)).status_code == 401
    assert (await client.get(PANEL_URL)).status_code == bearer_status


# --- CSRF: a sessão por cookie exige um cabeçalho que outra página não consegue enviar ---------


@pytest.mark.asyncio
async def test_panel_auth_mutation_without_panel_header_is_rejected(client, access):
    response = await client.delete("/api/tours/x", headers=_jwt_header(access.token()))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_panel_auth_mutation_with_panel_header_reaches_the_route(client, access):
    headers = _jwt_header(access.token()) | {"X-Panel-Request": "1"}

    response = await client.delete("/api/tours/x", headers=headers)

    assert response.status_code == 404


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

    await client.delete("/api/tours/x", headers=_jwt_header(token) | {"X-Panel-Request": "1"})

    logged = app_log_text(caplog)
    assert "pessoa-123" in logged
    assert "pessoa@exemplo.com" not in logged
    assert token not in logged


@pytest.mark.asyncio
async def test_panel_auth_never_logs_the_jwt_or_email(client, access, caplog):
    caplog.set_level(logging.DEBUG)
    token = access.token()

    await _get_panel(client, token)
    await _get_panel(client, access.token(exp=1))

    logged = app_log_text(caplog, loggers=("app", "uvicorn"))
    assert token not in logged
    assert "pessoa@exemplo.com" not in logged


# --- Elevação: as credenciais do painel e do n8n não se misturam -----------------------------


@pytest.mark.asyncio
async def test_ingest_rejects_the_panel_jwt(client, access, ingest_token):
    headers = _jwt_header(access.token())

    response = await client.post(INGEST_URL, json=valid_payload(), headers=headers)

    assert response.status_code == 401
