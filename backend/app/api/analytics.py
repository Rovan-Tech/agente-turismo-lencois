"""Tela Análises: indicadores agregados sobre conversas, atendimento e passeios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.services.analytics import InvalidPeriodError, compute_analytics

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_dashboard_auth)]
)


@router.get("")
async def get_analytics(
    periodo_dias: int = Query(30), db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Indicadores do período pedido (7, 30 ou 90 dias) e do período imediatamente anterior."""
    try:
        return await compute_analytics(db, periodo_dias)
    except InvalidPeriodError:
        raise HTTPException(status_code=422, detail="período inválido: use 7, 30 ou 90") from None
