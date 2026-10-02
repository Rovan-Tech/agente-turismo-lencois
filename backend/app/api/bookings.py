"""Rotas de agendamento com pagamento simulado (nenhum gateway real é integrado)."""

from __future__ import annotations

import re
from datetime import MAXYEAR, MINYEAR, date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_dashboard_auth
from app.core.access_jwt import AccessIdentity
from app.db.session import get_db
from app.models.booking import Booking, PaymentMethod
from app.services import booking_service, tour_catalog

router = APIRouter(
    prefix="/api/tours", tags=["bookings"], dependencies=[Depends(require_dashboard_auth)]
)

_PHONE_PATTERN = r"^\+?\d{8,15}$"


class BookingCreate(BaseModel):
    """Payload de um agendamento novo — sempre entra como pago (é a simulação)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    # `date` e `Enum` são as exceções ao strict mode previstas na PY-3: o JSON só expressa string,
    # nunca um `date` nem uma instância de `PaymentMethod` nativamente.
    data: date = Field(strict=False)
    pessoas: int = Field(gt=0, le=50)
    forma_pagamento: PaymentMethod = Field(strict=False)
    telefone: str | None = Field(default=None, max_length=32, pattern=_PHONE_PATTERN)


def _booking_dict(booking: Booking) -> dict[str, object]:
    """Serializa um agendamento para o formato usado pelo painel."""
    return {
        "id": booking.id,
        "tour_id": booking.tour_id,
        "data": booking.data.isoformat(),
        "pessoas": booking.pessoas,
        "forma_pagamento": booking.forma_pagamento,
        "status_pagamento": booking.status_pagamento,
        "telefone": booking.telefone,
        "created_at": booking.created_at.isoformat(),
    }


_MONTHS_IN_YEAR = 12
_YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _parse_year_month(mes: str) -> tuple[int, int]:
    """Converte ``YYYY-MM`` em `(ano, mês)`; levanta `ValueError` se o formato for inválido."""
    if not _YEAR_MONTH_PATTERN.match(mes):
        raise ValueError(mes)
    year_text, month_text = mes.split("-")
    year, month = int(year_text), int(month_text)
    # `date(year, ...)` só aceita 1..9999 (datetime.MINYEAR/MAXYEAR); ano 0 derrubaria a rota com
    # um 500 em vez de um 422 (entrada do usuário tem que ser validada na fronteira).
    if not (MINYEAR <= year <= MAXYEAR) or not (1 <= month <= _MONTHS_IN_YEAR):
        raise ValueError(mes)
    return year, month


@router.get("/{tour_id}/agenda")
async def get_tour_agenda(
    tour_id: str,
    mes: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    """Ocupação dia a dia de um mês inteiro, para desenhar o calendário do passeio.

    Args:
        tour_id: id do passeio.
        mes: mês no formato ``YYYY-MM``.
        db: sessão assíncrona injetada pelo FastAPI.

    Returns:
        Um item por dia do mês, com ``data``, ``capacidade`` e ``ocupadas``.

    Raises:
        HTTPException: 422 se ``mes`` não estiver no formato ``YYYY-MM``, 404 se o passeio não
            existir.
    """
    try:
        year, month = _parse_year_month(mes)
    except ValueError as exc:
        # Mesmo formato de `HTTPValidationError` que o FastAPI usa nos 422 próprios (`ingest.py`
        # segue o mesmo padrão): o schemathesis valida todo 422 da rota contra esse shape, e um
        # `detail` string quebraria o contrato documentado no OpenAPI.
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["query", "mes"],
                    "msg": "mes deve estar no formato YYYY-MM",
                }
            ],
        ) from exc
    try:
        days = await booking_service.get_monthly_occupancy(db, tour_id, year, month)
    except tour_catalog.TourNotFoundError as exc:
        raise HTTPException(status_code=404, detail="passeio não encontrado") from exc
    return [
        {"data": day.data.isoformat(), "capacidade": day.capacidade, "ocupadas": day.ocupadas}
        for day in days
    ]


@router.get("/{tour_id}/agendamentos")
async def list_day_bookings(
    tour_id: str, data: date, db: AsyncSession = Depends(get_db)
) -> list[dict[str, object]]:
    """Agendamentos pagos de um passeio num dia específico.

    Raises:
        HTTPException: 404 se o passeio não existir.
    """
    try:
        bookings = await booking_service.get_day_bookings(db, tour_id, data)
    except tour_catalog.TourNotFoundError as exc:
        raise HTTPException(status_code=404, detail="passeio não encontrado") from exc
    return [_booking_dict(booking) for booking in bookings]


@router.post("/{tour_id}/agendamentos", status_code=201)
async def create_booking(
    tour_id: str, payload: BookingCreate, http_request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Cria um agendamento (sempre pago — é a simulação de "pagamento aprovado").

    Args:
        tour_id: id do passeio.
        payload: dados do agendamento, já validados.
        http_request: requisição crua: ator (Access), IP e user-agent da trilha de auditoria.
        db: sessão assíncrona injetada pelo FastAPI.

    Returns:
        O agendamento criado, mais ``capacidade`` e ``ocupadas`` do dia já atualizados.

    Raises:
        HTTPException: 404 se o passeio não existir, 409 se não houver vagas suficientes.
    """
    request = booking_service.NewBookingRequest(
        data=payload.data,
        pessoas=payload.pessoas,
        forma_pagamento=payload.forma_pagamento,
        telefone=payload.telefone,
    )
    # Com o JWT do Access o `sub` identifica a pessoa; só o token fixo (sem ninguém por trás) cai
    # em "dashboard".
    identity = getattr(http_request.state, "identity", None)
    context = booking_service.RequestContext(
        actor=identity.sub if isinstance(identity, AccessIdentity) else "dashboard",
        ip=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("user-agent"),
    )
    try:
        result = await booking_service.create_booking(db, tour_id, request, context)
    except tour_catalog.TourNotFoundError as exc:
        raise HTTPException(status_code=404, detail="passeio não encontrado") from exc
    except booking_service.InsufficientCapacityError as exc:
        raise HTTPException(status_code=409, detail="não há vagas suficientes nesse dia") from exc
    return {
        **_booking_dict(result.booking),
        "capacidade": result.capacidade,
        "ocupadas": result.ocupadas,
    }
