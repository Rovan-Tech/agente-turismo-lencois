"""Apoio dos testes do login do painel: JWTs do Access de teste e requisições ao painel."""

import base64
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

KID = "kid-de-teste"
AUDIENCE = "aud-do-aplicativo-de-teste"
PANEL_URL = "/api/conversations"
NO_BEARER = {"Authorization": ""}


@dataclass
class AccessEnv:
    """Equipe do Access de teste: emite JWTs e conta quantas vezes o JWKS foi buscado."""

    issuer: str
    private_key: RSAPrivateKey
    other_key: RSAPrivateKey
    fetches: list[int]

    def token(self, *, key: RSAPrivateKey | None = None, kid: str = KID, **claims: object) -> str:
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


def jwt_header(token: str) -> dict[str, str]:
    return {**NO_BEARER, "Cf-Access-Jwt-Assertion": token}


def panel_headers(token: str) -> dict[str, str]:
    """Cabeçalhos de quem está logado no painel e faz uma mudança (JWT mais o cabeçalho de CSRF)."""
    return jwt_header(token) | {"X-Panel-Request": "1"}


async def get_panel(client: httpx.AsyncClient, token: str) -> httpx.Response:
    return await client.get(PANEL_URL, headers=jwt_header(token))


async def get_panel_times(client: httpx.AsyncClient, token: str, times: int) -> None:
    for _ in range(times):
        await get_panel(client, token)


def b64(data: Mapping[str, object]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
