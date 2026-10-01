import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

import pytest
from sqlalchemy import Executable, Select, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState

from app.models.booking import Booking, PaymentMethod, PaymentStatus
from app.models.tour import Tour
from app.services import booking_service, tour_catalog
from tests.conftest import default_tour_fields, persist


@asynccontextmanager
async def _spy_on_execute(db_session: AsyncSession) -> AsyncIterator[list[Executable]]:
    """Captura as declarações passadas a `db_session.execute`, via o evento `do_orm_execute`
    (sem trocar o método em si), pra inspecionar o SQL montado — prova mitigações que o resultado
    da consulta sozinho não denunciaria, como `FOR UPDATE`."""
    captured: list[Executable] = []

    def capture(state: ORMExecuteState) -> None:
        captured.append(state.statement)

    event.listen(db_session.sync_session, "do_orm_execute", capture)
    try:
        yield captured
    finally:
        event.remove(db_session.sync_session, "do_orm_execute", capture)


def _tour(*, capacidade_diaria: int = 10, ativo: bool = True) -> Tour:
    return Tour(**default_tour_fields(capacidade_diaria=capacidade_diaria, ativo=ativo))


def _request(
    *,
    data: date = date(2026, 9, 28),
    pessoas: int = 3,
    forma_pagamento: PaymentMethod = PaymentMethod.PIX,
    telefone: str | None = "5598999998888",
) -> booking_service.NewBookingRequest:
    return booking_service.NewBookingRequest(
        data=data, pessoas=pessoas, forma_pagamento=forma_pagamento, telefone=telefone
    )


def _context() -> booking_service.RequestContext:
    return booking_service.RequestContext(actor="dashboard", ip="203.0.113.10", user_agent="pytest")


def _other_booking(data: date, status: PaymentStatus, *, pessoas: int = 4) -> Booking:
    """Agendamento que não deve contar pra ocupação nem aparecer na lista do dia 28/09."""
    return Booking(
        tour_id="passeio-teste",
        data=data,
        pessoas=pessoas,
        forma_pagamento=PaymentMethod.PIX,
        status_pagamento=status,
    )


async def _create(
    db_session: AsyncSession,
    tour_id: str = "passeio-teste",
    *,
    data: date = date(2026, 9, 28),
    pessoas: int = 3,
) -> booking_service.BookingResult:
    request = _request(data=data, pessoas=pessoas)
    return await booking_service.create_booking(db_session, tour_id, request, _context())


@pytest.mark.asyncio
async def test_create_booking_persists_as_paid(db_session):
    await persist(db_session, _tour())

    result = await _create(db_session)

    assert result.booking.status_pagamento.value == "pago"
    assert result.ocupadas == 3
    assert result.capacidade == 10


@pytest.mark.asyncio
async def test_create_booking_rejects_unknown_tour(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await _create(db_session)


@pytest.mark.asyncio
async def test_create_booking_rejects_inactive_tour(db_session):
    await persist(db_session, _tour(ativo=False))

    with pytest.raises(tour_catalog.TourNotFoundError):
        await _create(db_session)


@pytest.mark.asyncio
async def test_create_booking_rejects_when_second_booking_would_exceed_capacity(db_session):
    await persist(db_session, _tour(capacidade_diaria=5))
    await _create(db_session, pessoas=4)

    with pytest.raises(booking_service.InsufficientCapacityError):
        await _create(db_session, pessoas=2)


@pytest.mark.asyncio
async def test_create_booking_accepts_a_booking_that_exactly_fills_capacity(db_session):
    await persist(db_session, _tour(capacidade_diaria=5))

    result = await _create(db_session, pessoas=5)

    assert result.ocupadas == 5


@pytest.mark.asyncio
async def test_create_booking_does_not_count_pending_bookings_against_capacity(db_session):
    """Sem o filtro `status_pagamento == PAGO` na recontagem, 4 (pendente) + 3 (novo) estouraria a
    capacidade 5 e isto levantaria `InsufficientCapacityError` à toa."""
    pending = _other_booking(date(2026, 9, 28), PaymentStatus.PENDENTE, pessoas=4)
    await persist(db_session, _tour(capacidade_diaria=5), pending)

    result = await _create(db_session, pessoas=3)

    assert result.ocupadas == 3


@pytest.mark.asyncio
async def test_create_booking_locks_the_tour_row_for_update(db_session):
    """Prova a mitigação de TOCTOU do threat model: sem `with_for_update()`, o mutante sobrevive.

    Não dá pra exercitar o lock físico em SQLite (o dialeto ignora `FOR UPDATE`), mas o teste
    prova que a consulta realmente pede o lock na linha do `Tour` — removê-lo quebra este teste.
    """
    await persist(db_session, _tour())

    async with _spy_on_execute(db_session) as captured:
        await _create(db_session)

    locked = [stmt for stmt in captured if getattr(stmt, "_for_update_arg", None) is not None]
    assert locked, "nenhuma consulta pediu FOR UPDATE"


@pytest.mark.asyncio
async def test_create_booking_logs_structured_event_without_phone(db_session, caplog):
    await persist(db_session, _tour())

    with caplog.at_level(logging.INFO):
        result = await _create(db_session)

    [record] = caplog.records
    assert record.event == "booking_created"
    assert record.booking_id == result.booking.id
    assert record.ocupadas_antes == 0
    assert record.ocupadas_depois == 3
    assert record.ator == "dashboard"
    assert record.ip == "203.0.113.10"
    assert "telefone" not in vars(record)
    assert "5598999998888" not in caplog.text


@pytest.mark.parametrize(
    ("excluded_data", "excluded_status"),
    [(date(2026, 9, 29), PaymentStatus.PAGO), (date(2026, 9, 28), PaymentStatus.PENDENTE)],
    ids=["outro-dia", "pendente"],
)
@pytest.mark.asyncio
async def test_get_day_bookings_excludes_what_isnt_paid_for_that_day(
    db_session, excluded_data, excluded_status
):
    await persist(db_session, _tour(), _other_booking(excluded_data, excluded_status))
    await _create(db_session, data=date(2026, 9, 28))

    bookings = await booking_service.get_day_bookings(
        db_session, "passeio-teste", date(2026, 9, 28)
    )

    assert [b.data for b in bookings] == [date(2026, 9, 28)]


@pytest.mark.asyncio
async def test_get_day_bookings_rejects_unknown_tour(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await booking_service.get_day_bookings(db_session, "nao-existe", date(2026, 9, 28))


@pytest.mark.asyncio
async def test_get_monthly_occupancy_covers_every_day_with_zero_by_default(db_session):
    await persist(db_session, _tour(capacidade_diaria=10))
    await _create(db_session, data=date(2026, 9, 5), pessoas=4)

    days = await booking_service.get_monthly_occupancy(db_session, "passeio-teste", 2026, 9)

    assert len(days) == 30
    occupied_by_day = {day.data: day.ocupadas for day in days}
    assert occupied_by_day[date(2026, 9, 5)] == 4
    assert occupied_by_day[date(2026, 9, 6)] == 0
    assert all(day.capacidade == 10 for day in days)


@pytest.mark.asyncio
async def test_get_monthly_occupancy_excludes_pending_bookings_from_the_sum(db_session):
    pending = _other_booking(date(2026, 9, 5), PaymentStatus.PENDENTE)
    await persist(db_session, _tour(capacidade_diaria=10), pending)

    days = await booking_service.get_monthly_occupancy(db_session, "passeio-teste", 2026, 9)

    assert all(day.ocupadas == 0 for day in days)


@pytest.mark.asyncio
async def test_get_monthly_occupancy_only_fetches_the_requested_month(db_session):
    """A agregação SQL já recorta `data BETWEEN` o mês pedido (performance: não varre o histórico
    todo do passeio a cada calendário aberto). O resultado por dia não denunciaria a falta desse
    filtro sozinho — o próprio laço só pergunta pelas datas do mês —, então o teste olha a consulta
    montada em vez do resultado."""
    await persist(db_session, _tour(capacidade_diaria=10))

    async with _spy_on_execute(db_session) as captured:
        await booking_service.get_monthly_occupancy(db_session, "passeio-teste", 2026, 9)

    aggregation = next(stmt for stmt in captured if getattr(stmt, "_group_by_clauses", None))
    assert isinstance(aggregation, Select)
    compiled = aggregation.compile(compile_kwargs={"literal_binds": True})
    assert "BETWEEN" in str(compiled).upper()


@pytest.mark.asyncio
async def test_get_monthly_occupancy_rejects_unknown_tour(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await booking_service.get_monthly_occupancy(db_session, "nao-existe", 2026, 9)
