"""Autenticação das rotas: painel (token fixo ou JWT do Cloudflare Access) e entrada do n8n."""

from __future__ import annotations

import logging

from fastapi import Depends, Header, HTTPException, Request

from app.core.access_jwt import (
    AccessAuthError,
    AccessIdentity,
    AccessUnavailableError,
    verify_access_jwt,
)
from app.core.config import Settings, get_settings
from app.core.security import is_valid_bearer_token, is_valid_dashboard_token

logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PANEL_REQUEST_HEADER_VALUE = "1"


async def _identity_from_access_jwt(token: str, settings: Settings) -> AccessIdentity:
    """Valida o JWT do Access; sem equipe e audiência configuradas, recusa tudo (falha fechada)."""
    if not settings.access_team_domain or not settings.access_aud:
        raise HTTPException(status_code=401, detail="não autorizado")
    try:
        return await verify_access_jwt(token, settings.access_team_domain, settings.access_aud)
    except AccessAuthError:
        raise HTTPException(status_code=401, detail="não autorizado") from None
    except AccessUnavailableError as error:
        cause = type(error.__cause__).__name__ if error.__cause__ else "em espera"
        logger.exception(
            "chaves do Cloudflare Access indisponíveis (%s)",
            cause,
            exc_info=False,
            extra={"event": "access_jwks", "cause": cause},
        )
        raise HTTPException(status_code=503, detail="autenticação indisponível") from None


def _require_panel_header(request: Request, header_value: str | None) -> None:
    """Exige o cabeçalho do painel em toda mutação (contra CSRF).

    O cookie do Access é enviado sozinho pelo navegador; já um cabeçalho próprio uma página de
    terceiro não consegue mandar sem a pré-verificação do CORS, que o painel não libera.
    """
    if request.method not in SAFE_METHODS and header_value != PANEL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=403, detail="cabeçalho do painel ausente")


async def require_dashboard_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    cf_access_jwt_assertion: str | None = Header(default=None),
    x_panel_request: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Protege as rotas do painel conforme `PANEL_AUTH_MODE` (ADR-0006); fail-closed.

    `token` aceita só o token fixo, `access` só o JWT do Cloudflare Access e `both` os dois. Os
    cabeçalhos de identidade do Access (como o e-mail) nunca são lidos: só as claims do JWT
    verificado.

    Raises:
        HTTPException: 401 sem credencial válida; 403 em mutação sem o cabeçalho do painel; 503 se
            as chaves do Access não puderem ser buscadas.
    """
    mode = settings.panel_auth_mode
    if mode != "access" and is_valid_dashboard_token(authorization, settings.dashboard_api_token):
        return
    if mode == "token" or not cf_access_jwt_assertion:
        raise HTTPException(status_code=401, detail="não autorizado")
    identity = await _identity_from_access_jwt(cf_access_jwt_assertion, settings)
    request.state.identity = identity
    _require_panel_header(request, x_panel_request)
    if request.method not in SAFE_METHODS:
        # Só o `sub` (opaco): nem o e-mail nem o JWT entram no log. Vai o molde da rota
        # (`/api/tours/{tour_id}`), não o caminho cru, que o cliente controla.
        route_path = getattr(request.scope.get("route"), "path", "?")
        logger.info(
            "mutação no painel: %s %s por %s",
            request.method,
            route_path,
            identity.sub,
            extra={"event": "panel_mutation", "actor": identity.sub},
        )


async def require_panel_identity(request: Request) -> AccessIdentity:
    """Exige uma pessoa logada (JWT do Access): o token fixo do painel não diz quem agiu.

    Roda depois de `require_dashboard_auth` (dependência do roteador), que guarda a identidade.

    Raises:
        HTTPException: 403 se a autenticação foi pelo token fixo, sem uma pessoa por trás.
    """
    identity = getattr(request.state, "identity", None)
    if not isinstance(identity, AccessIdentity):
        raise HTTPException(status_code=403, detail="entre com o seu login para fazer isto")
    return identity


async def require_ingest_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Protege a rota de entrada do n8n com o token próprio (nunca o do painel); fail-closed."""
    if not is_valid_bearer_token(authorization, settings.ingest_api_token):
        raise HTTPException(status_code=401, detail="não autorizado")
