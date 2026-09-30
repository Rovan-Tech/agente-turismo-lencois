"""Regras de negócio do catálogo de passeios (CRUD), sem depender do FastAPI."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tour import Tour


class TourAlreadyExistsError(Exception):
    """Levantado ao tentar criar um passeio com ``id`` já existente."""


class TourNotFoundError(Exception):
    """Levantado ao editar/desativar um passeio que não existe."""


async def list_tours(db: AsyncSession, *, incluir_inativos: bool) -> list[Tour]:
    """Lista o catálogo de passeios.

    Args:
        db: sessão assíncrona.
        incluir_inativos: quando ``True``, inclui também os passeios desativados.

    Returns:
        Passeios ativos, ou todos se ``incluir_inativos`` for ``True``.
    """
    query = select(Tour) if incluir_inativos else select(Tour).where(Tour.ativo.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_tour(db: AsyncSession, tour_id: str) -> Tour:
    """Busca um passeio pelo id.

    Args:
        db: sessão assíncrona.
        tour_id: id do passeio.

    Returns:
        O passeio encontrado.

    Raises:
        TourNotFoundError: se não existir passeio com esse id.
    """
    tour = await db.get(Tour, tour_id)
    if tour is None:
        raise TourNotFoundError(tour_id)
    return tour


async def create_tour(db: AsyncSession, fields: dict[str, object]) -> Tour:
    """Cria um novo passeio.

    Args:
        db: sessão assíncrona.
        fields: campos validados do passeio (inclui ``id``).

    Returns:
        O passeio criado.

    Raises:
        TourAlreadyExistsError: se já existir um passeio com o mesmo ``id``.
    """
    tour = Tour(**fields)
    db.add(tour)
    try:
        await db.commit()
    except IntegrityError as exc:
        # Só a PK (id) pode colidir aqui: os campos vêm validados pelo Pydantic e a tabela não
        # tem outra constraint. Se isso mudar, revisar essa tradução pra TourAlreadyExistsError.
        await db.rollback()
        raise TourAlreadyExistsError(fields["id"]) from exc
    return tour


async def update_tour(db: AsyncSession, tour_id: str, fields: dict[str, object]) -> Tour:
    """Substitui os campos de um passeio existente; levanta ``TourNotFoundError`` se sumir."""
    tour = await get_tour(db, tour_id)
    for field, value in fields.items():
        setattr(tour, field, value)
    await db.commit()
    return tour


async def deactivate_tour(db: AsyncSession, tour_id: str) -> Tour:
    """Desativa um passeio (soft delete, nunca apaga); levanta ``TourNotFoundError`` se sumir."""
    tour = await get_tour(db, tour_id)
    tour.ativo = False
    await db.commit()
    return tour
