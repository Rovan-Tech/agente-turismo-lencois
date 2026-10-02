"""Regras de negócio do agendamento com pagamento simulado, sem depender do FastAPI."""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, PaymentMethod, PaymentStatus
from app.models.tour import Tour
from app.services import tour_catalog

logger = logging.getLogger(__name__)


class InsufficientCapacityError(Exception):
    """Levantado quando um agendamento novo estouraria a capacidade diária do passeio."""

    def __init__(self, tour_id: str, day: date) -> None:
        """Guarda o id do passeio e o dia que não tinha vagas suficientes."""
        self.tour_id = tour_id
        self.day = day
        super().__init__(f"{tour_id} sem vagas em {day.isoformat()}")


@dataclass(slots=True, frozen=True)
class DayOccupancy:
    """Ocupação de um passeio num dia (usada para desenhar o calendário)."""

    data: date
    capacidade: int
    ocupadas: int


@dataclass(slots=True, frozen=True)
class NewBookingRequest:
    """Dados de um agendamento novo — sempre entra como pago (é a simulação)."""

    data: date
    pessoas: int
    forma_pagamento: PaymentMethod
    telefone: str | None = None


@dataclass(slots=True, frozen=True)
class RequestContext:
    """Quem fez a chamada, pra trilha de auditoria provisória.

    DATA-3, ⏳ TD-A5: sem tabela append-only nem hash chain ainda, log estruturado com
    quem/quando/estado anterior e novo é o que a base atual permite.
    """

    actor: str
    ip: str | None
    user_agent: str | None


@dataclass(slots=True, frozen=True)
class BookingResult:
    """Agendamento criado mais a ocupação do dia já atualizada (evita uma segunda consulta)."""

    booking: Booking
    ocupadas: int
    capacidade: int


async def _get_active_tour(db: AsyncSession, tour_id: str) -> Tour:
    """Busca o passeio e recusa o desativado: fora do catálogo, fora do agendamento.

    Raises:
        tour_catalog.TourNotFoundError: se não existir passeio com esse id, ou se existir mas
            estiver desativado (mesmo tratamento de `create_booking`: para quem agenda, um
            passeio fora do catálogo é como se não existisse).
    """
    tour = await tour_catalog.get_tour(db, tour_id)
    if not tour.ativo:
        raise tour_catalog.TourNotFoundError(tour_id)
    return tour


async def get_monthly_occupancy(
    db: AsyncSession, tour_id: str, year: int, month: int
) -> list[DayOccupancy]:
    """Ocupação dia a dia de um mês inteiro, mesmo nos dias sem agendamento.

    Args:
        db: sessão assíncrona.
        tour_id: id do passeio.
        year: ano (ex.: 2026).
        month: mês (1-12).

    Returns:
        Um `DayOccupancy` por dia do mês, na ordem do calendário.

    Raises:
        tour_catalog.TourNotFoundError: se o passeio não existir ou estiver desativado.
    """
    tour = await _get_active_tour(db, tour_id)
    _, days_in_month = calendar.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, days_in_month)
    result = await db.execute(
        select(Booking.data, func.sum(Booking.pessoas))
        .where(Booking.tour_id == tour_id)
        .where(Booking.status_pagamento == PaymentStatus.PAGO)
        .where(Booking.data.between(start, end))
        .group_by(Booking.data)
    )
    occupied_by_day = {day: int(total) for day, total in result.all()}
    return [
        DayOccupancy(
            data=start.replace(day=day),
            capacidade=tour.capacidade_diaria,
            ocupadas=occupied_by_day.get(start.replace(day=day), 0),
        )
        for day in range(1, days_in_month + 1)
    ]


async def get_day_bookings(db: AsyncSession, tour_id: str, day: date) -> list[Booking]:
    """Agendamentos pagos de um passeio num dia específico, do mais antigo ao mais novo.

    Raises:
        tour_catalog.TourNotFoundError: se não existir passeio com esse id, ou se estiver
            desativado (mesmo contrato de `get_monthly_occupancy`, pra não devolver lista vazia
            disfarçando um `tour_id` inválido ou fora do catálogo).
    """
    await _get_active_tour(db, tour_id)
    result = await db.execute(
        select(Booking)
        .where(Booking.tour_id == tour_id)
        .where(Booking.data == day)
        .where(Booking.status_pagamento == PaymentStatus.PAGO)
        .order_by(Booking.created_at)
    )
    return list(result.scalars().all())


async def _paid_people_on_day(db: AsyncSession, tour_id: str, day: date) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(Booking.pessoas), 0))
        .where(Booking.tour_id == tour_id)
        .where(Booking.data == day)
        .where(Booking.status_pagamento == PaymentStatus.PAGO)
    )
    return result.scalar_one()


async def create_booking(
    db: AsyncSession, tour_id: str, request: NewBookingRequest, context: RequestContext
) -> BookingResult:
    """Cria um agendamento já como pago (reflete "simular pagamento aprovado").

    A consulta abaixo (não `tour_catalog.get_tour`) trava a linha do passeio
    (`SELECT ... FOR UPDATE`) e reconta as vagas do dia dentro da mesma transação antes de
    decidir — fecha a janela de corrida entre dois agendamentos quase simultâneos (ver
    `docs/threat-models/2026-09-30-agendamento-pagamento-simulado.md`). Em SQLite (dev/testes) o
    lock não é real (o dialeto não suporta `FOR UPDATE`), mas a recontagem na mesma transação já
    prova a lógica; em produção (Postgres) o lock é efetivo.

    Args:
        db: sessão assíncrona.
        tour_id: id do passeio.
        request: dados do agendamento (já validados pelo schema de entrada).
        context: ator, IP e user-agent da chamada, pra trilha de auditoria (DATA-3).

    Returns:
        O agendamento criado e a ocupação do dia depois dele.

    Raises:
        tour_catalog.TourNotFoundError: se o passeio não existir ou estiver desativado.
        InsufficientCapacityError: se não houver vagas suficientes no dia.
    """
    tour_result = await db.execute(select(Tour).where(Tour.id == tour_id).with_for_update())
    tour = tour_result.scalar_one_or_none()
    if tour is None or not tour.ativo:
        raise tour_catalog.TourNotFoundError(tour_id)

    occupied_before = await _paid_people_on_day(db, tour_id, request.data)
    if occupied_before + request.pessoas > tour.capacidade_diaria:
        raise InsufficientCapacityError(tour_id, request.data)

    booking = Booking(
        tour_id=tour_id,
        data=request.data,
        pessoas=request.pessoas,
        forma_pagamento=request.forma_pagamento,
        status_pagamento=PaymentStatus.PAGO,
        telefone=request.telefone,
    )
    db.add(booking)
    await db.commit()
    occupied_after = occupied_before + request.pessoas
    _log_booking_created(booking, context, occupied_before, occupied_after)
    return BookingResult(
        booking=booking, ocupadas=occupied_after, capacidade=tour.capacidade_diaria
    )


def _log_booking_created(
    booking: Booking, context: RequestContext, occupied_before: int, occupied_after: int
) -> None:
    """Trilha de auditoria provisória da criação (DATA-3, ⏳ TD-A5): nunca inclui o telefone."""
    logger.info(
        "booking criado",
        extra={
            "event": "booking_created",
            "booking_id": booking.id,
            "tour_id": booking.tour_id,
            "data": booking.data.isoformat(),
            "pessoas": booking.pessoas,
            "forma_pagamento": booking.forma_pagamento.value,
            "ocupadas_antes": occupied_before,
            "ocupadas_depois": occupied_after,
            "ator": context.actor,
            "ip": context.ip,
            "user_agent": context.user_agent,
        },
    )
