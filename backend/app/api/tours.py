"""Rotas de gestão do catálogo de passeios (leitura e CRUD, autenticadas pelo painel)."""

from __future__ import annotations

from collections.abc import Awaitable

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_dashboard_auth
from app.api.errors import CONFLICT, NOT_FOUND, TOUR_NOT_FOUND
from app.db.session import get_db
from app.models.tour import DifficultyLevel, Tour
from app.services import tour_catalog

router = APIRouter(
    prefix="/api/tours", tags=["tours"], dependencies=[Depends(require_dashboard_auth)]
)

_ID_PATTERN = r"^[a-z0-9-]+$"


class TourFields(BaseModel):
    """Campos comuns de criação/edição de um passeio (sem ``id``, que é imutável)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(min_length=1, max_length=1000)
    dificuldade_fisica: DifficultyLevel
    caminhada_areia_minutos: int = Field(ge=0, le=600)
    acessivel_idosos: bool
    acessivel_cadeirantes: bool
    acessivel_criancas_pequenas: bool
    duracao_horas: float = Field(gt=0, le=24, allow_inf_nan=False)
    faixa_etaria_recomendada: str = Field(min_length=1, max_length=200)
    preco_reais: float = Field(ge=0, le=99_999_999.99, allow_inf_nan=False)


class TourCreate(TourFields):
    """Payload de criação de um passeio: os campos de ``TourFields`` mais o ``id``."""

    id: str = Field(min_length=1, max_length=64, pattern=_ID_PATTERN)
    ativo: bool = True


class TourUpdate(TourFields):
    """Payload de edição: substitui todos os campos, incluindo ``ativo`` (sem padrão)."""

    ativo: bool


def _to_dict(tour: Tour) -> dict[str, object]:
    """Serializa um passeio para o formato usado pelo painel (inclui ``ativo``).

    Args:
        tour: passeio a serializar.

    Returns:
        Dicionário com todos os atributos do catálogo mais o estado ``ativo``.
    """
    return {**tour.to_catalog_dict(), "ativo": tour.ativo}


async def _get_or_404(coro: Awaitable[Tour]) -> Tour:
    try:
        return await coro
    except tour_catalog.TourNotFoundError as exc:
        raise HTTPException(status_code=404, detail=TOUR_NOT_FOUND) from exc


@router.get("")
async def list_tours(
    incluir_inativos: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    """Lista o catálogo de passeios.

    Args:
        incluir_inativos: quando ``True``, inclui também os passeios desativados.
        db: sessão assíncrona injetada pelo FastAPI.

    Returns:
        Lista de passeios no formato de dicionário.
    """
    tours = await tour_catalog.list_tours(db, incluir_inativos=incluir_inativos)
    return [_to_dict(tour) for tour in tours]


@router.post("", status_code=201, responses={409: CONFLICT})
async def create_tour(payload: TourCreate, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Cria um novo passeio no catálogo.

    Args:
        payload: dados validados do novo passeio.
        db: sessão assíncrona injetada pelo FastAPI.

    Returns:
        O passeio criado.

    Raises:
        HTTPException: 409 se já existir um passeio com o mesmo ``id``.
    """
    try:
        tour = await tour_catalog.create_tour(db, payload.model_dump())
    except tour_catalog.TourAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="já existe um passeio com esse id") from exc
    return _to_dict(tour)


@router.put("/{tour_id}", responses={404: NOT_FOUND})
async def update_tour(
    tour_id: str,
    payload: TourUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Edita um passeio existente; levanta 404 se ``tour_id`` não existir."""
    tour = await _get_or_404(tour_catalog.update_tour(db, tour_id, payload.model_dump()))
    return _to_dict(tour)


@router.delete("/{tour_id}", responses={404: NOT_FOUND})
async def deactivate_tour(tour_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Desativa um passeio (soft delete, nunca apaga); levanta 404 se ``tour_id`` não existir."""
    tour = await _get_or_404(tour_catalog.deactivate_tour(db, tour_id))
    return _to_dict(tour)
