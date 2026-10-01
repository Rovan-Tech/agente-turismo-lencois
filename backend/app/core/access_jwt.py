"""Validação do JWT que o Cloudflare Access injeta nas requisições do painel (ADR-0006)."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

JWKS_CACHE_SECONDS = 300
JWKS_TIMEOUT_SECONDS = 5
# Depois de uma falha ao buscar as chaves, as próximas requisições recebem 503 na hora em vez de
# esperar, cada uma, o timeout do fetch (a busca é serializada pelo cliente do PyJWT).
JWKS_DOWN_SECONDS = 15
JWKS_USER_AGENT = "agente-turismo-lencois/1.0 (validacao do JWT do Access)"
CLOCK_SKEW_SECONDS = 30
REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]


class AccessAuthError(Exception):
    """JWT inválido: assinatura, validade, emissor, audiência ou claims fora do esperado."""


class AccessUnavailableError(Exception):
    """As chaves públicas do Access não puderam ser buscadas (falha fechada, não é culpa do JWT)."""


@dataclass(frozen=True, slots=True)
class AccessIdentity:
    """Quem fez a requisição: o `sub` do JWT, identificador opaco da pessoa no Access."""

    sub: str


_jwks_down_until: dict[str, float] = {}


@lru_cache(maxsize=4)
def _jwks_client(team_domain: str) -> jwt.PyJWKClient:
    """Um cliente por equipe: guarda o JWKS por 5 minutos em vez de buscá-lo a cada requisição."""
    return jwt.PyJWKClient(
        f"{team_domain}/cdn-cgi/access/certs",
        cache_jwk_set=True,
        lifespan=JWKS_CACHE_SECONDS,
        timeout=JWKS_TIMEOUT_SECONDS,
        headers={"User-Agent": JWKS_USER_AGENT},
    )


def _signing_key(token: str, team_domain: str) -> jwt.PyJWK:
    """Chave pública que assinou o token; busca falha vira indisponibilidade, não 401."""
    if time.monotonic() < _jwks_down_until.get(team_domain, 0.0):
        raise AccessUnavailableError
    try:
        return _jwks_client(team_domain).get_signing_key_from_jwt(token)
    except (PyJWKClientConnectionError, OSError, json.JSONDecodeError) as error:
        _jwks_down_until[team_domain] = time.monotonic() + JWKS_DOWN_SECONDS
        raise AccessUnavailableError from error
    except PyJWTError as error:
        raise AccessAuthError from error


def _verify(token: str, team_domain: str, audience: str) -> AccessIdentity:
    signing_key = _signing_key(token, team_domain)
    try:
        # O algoritmo vem do código, nunca do token: barra `alg: none` e HS256 com a chave pública.
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=team_domain,
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": REQUIRED_CLAIMS},
        )
    except PyJWTError as error:
        raise AccessAuthError from error
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise AccessAuthError
    return AccessIdentity(sub=sub)


async def verify_access_jwt(token: str, team_domain: str, audience: str) -> AccessIdentity:
    """Valida o JWT do Access e devolve quem é a pessoa.

    A busca do JWKS é bloqueante (urllib), então roda numa thread para não travar o servidor.

    Args:
        token: Valor do cabeçalho `Cf-Access-Jwt-Assertion`.
        team_domain: URL da equipe (`https://<equipe>.cloudflareaccess.com`), o emissor esperado.
        audience: AUD tag do aplicativo no Access.

    Returns:
        A identidade da pessoa.

    Raises:
        AccessAuthError: o JWT não vale para este aplicativo.
        AccessUnavailableError: não foi possível obter as chaves públicas do Access.
    """
    return await asyncio.to_thread(_verify, token, team_domain, audience)
