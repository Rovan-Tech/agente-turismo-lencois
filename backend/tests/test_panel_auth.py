"""Login do painel: o backend valida o JWT do Cloudflare Access (ADR-0006)."""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from jwt.exceptions import PyJWKClientConnectionError

from tests.access_support import (
    AUDIENCE,
    KID,
    NO_BEARER,
    PANEL_URL,
    b64,
    get_panel,
    get_panel_times,
)

# --- Spoofing: o JWT precisa ser autêntico, atual e destinado a este aplicativo ----------------


@pytest.mark.asyncio
async def test_panel_auth_accepts_a_valid_access_jwt_on_reads_without_the_panel_header(
    client, access
):
    assert (await get_panel(client, access.token())).status_code == 200


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
    response = await get_panel(client, access.token(**claims))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_a_tampered_signature(client, access):
    token = access.token()
    flipped = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    assert (await get_panel(client, flipped)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_a_token_signed_by_another_key(client, access):
    assert (await get_panel(client, access.token(key=access.other_key))).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_alg_none(client, access):
    now = int(time.time())
    claims = {"iss": access.issuer, "aud": [AUDIENCE], "sub": "x", "iat": now, "exp": now + 600}
    token = jwt.encode(claims, "", algorithm="none", headers={"kid": KID})

    assert (await get_panel(client, token)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_rejects_hs256_signed_with_the_public_key(client, access):
    """Confusão de algoritmo: o atacante assina com a chave pública, que é pública."""
    public_pem = access.private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": KID}
    claims = {"iss": access.issuer, "aud": [AUDIENCE], "sub": "x", "iat": now, "exp": now + 600}
    signing_input = f"{b64(header)}.{b64(claims)}"
    signature = hmac.new(public_pem, signing_input.encode(), hashlib.sha256).digest()
    token = f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    assert (await get_panel(client, token)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_unknown_kid_is_rejected(client, access):
    assert (await get_panel(client, access.token(kid="chave-desconhecida"))).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_ignores_identity_headers_without_a_valid_jwt(client, access):
    headers = {**NO_BEARER, "Cf-Access-Authenticated-User-Email": "pessoa@exemplo.com"}

    assert (await client.get(PANEL_URL, headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_panel_auth_error_does_not_echo_the_token(client, access):
    token = access.token(exp=1)

    response = await get_panel(client, token)

    assert token not in response.text


# --- Tampering e DoS: JWKS fora do ar, cache -------------------------------------------------


@pytest.mark.asyncio
async def test_panel_auth_jwks_failure_fails_closed(client, access, monkeypatch):
    def failing_fetch(self: object) -> dict[str, object]:
        raise PyJWKClientConnectionError

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", failing_fetch)

    response = await get_panel(client, access.token())

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_panel_auth_caches_the_jwks_between_requests(client, access):
    await get_panel_times(client, access.token(), 3)

    assert len(access.fetches) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [ConnectionResetError, json.JSONDecodeError("corpo", "", 0)],
    ids=["connection_reset", "invalid_json_body"],
)
async def test_panel_auth_any_failure_fetching_the_jwks_is_a_503(
    client, access, monkeypatch, failure
):
    """O fetch do JWKS falha de vários jeitos além de PyJWKClientConnectionError: todos são 503."""

    def failing_fetch(self: object) -> dict[str, object]:
        raise failure

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", failing_fetch)

    assert (await get_panel(client, access.token())).status_code == 503


@pytest.mark.asyncio
async def test_panel_auth_jwks_outage_is_remembered_instead_of_refetched_per_request(
    client, access, monkeypatch
):
    """Uma queda do Cloudflare não pode prender cada requisição por até o timeout do fetch."""
    attempts: list[int] = []

    def failing_fetch(self: object) -> dict[str, object]:
        attempts.append(1)
        raise PyJWKClientConnectionError

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", failing_fetch)
    token = access.token()

    statuses = [(await get_panel(client, token)).status_code for _ in range(3)]

    assert statuses == [503, 503, 503]
    assert len(attempts) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "status"),
    [(-10, 200), (-120, 401)],
    ids=["10s_expired_is_tolerated", "2min_expired_is_rejected"],
)
async def test_panel_auth_clock_skew_tolerance_is_small(client, access, offset, status):
    token = access.token(exp=int(time.time()) + offset)

    assert (await get_panel(client, token)).status_code == status
