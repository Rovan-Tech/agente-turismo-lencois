from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import is_valid_bearer_token, is_valid_dashboard_token


async def require_dashboard_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not is_valid_dashboard_token(authorization, settings.dashboard_api_token):
        raise HTTPException(status_code=401, detail="não autorizado")


async def require_ingest_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Protege a rota de entrada do n8n com o token próprio (nunca o do painel); fail-closed."""
    if not is_valid_bearer_token(authorization, settings.ingest_api_token):
        raise HTTPException(status_code=401, detail="não autorizado")
