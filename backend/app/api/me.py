"""Quem está logado no painel: o painel mostra ao atendente o nome que o turista vai ver."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_dashboard_auth, require_panel_identity
from app.core.access_jwt import AccessIdentity

router = APIRouter(prefix="/api/me", tags=["me"], dependencies=[Depends(require_dashboard_auth)])


@router.get("")
async def who_am_i(
    identity: AccessIdentity = Depends(require_panel_identity),
) -> dict[str, str | None]:
    """Devolve o `sub` da pessoa logada e o primeiro nome derivado do login (ou `None`)."""
    return {"sub": identity.sub, "nome": identity.first_name}
