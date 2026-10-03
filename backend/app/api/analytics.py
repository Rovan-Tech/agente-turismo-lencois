"""Tela Análises: indicadores agregados sobre conversas, atendimento e passeios."""

from __future__ import annotations

import enum

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.services.analytics import compute_analytics

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_dashboard_auth)]
)


class Periodo(int, enum.Enum):
    """Os três períodos que a tela oferece.

    `Literal[7, 30, 90]` não converte a string da query (`"30"`) para `int`; um `IntEnum` o
    FastAPI converte direito.
    """

    SETE_DIAS = 7
    TRINTA_DIAS = 30
    NOVENTA_DIAS = 90


@router.get("")
async def get_analytics(
    periodo_dias: Periodo = Query(Periodo.TRINTA_DIAS), db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Indicadores do período pedido (7, 30 ou 90 dias) e do período imediatamente anterior.

    `Periodo` já faz o FastAPI recusar qualquer outro valor com 422 no formato padrão dele (erro
    de validação, não um `HTTPException` nosso) — por isso não há mais nada pra tratar aqui.
    """
    return await compute_analytics(db, int(periodo_dias))
