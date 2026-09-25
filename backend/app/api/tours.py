from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.models.tour import Tour

router = APIRouter(
    prefix="/api/tours", tags=["tours"], dependencies=[Depends(require_dashboard_auth)]
)


@router.get("")
async def list_tours(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Tour).where(Tour.ativo.is_(True)))
    tours = result.scalars().all()
    return [t.to_catalog_dict() for t in tours]
