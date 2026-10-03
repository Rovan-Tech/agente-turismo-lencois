import pytest

from app.services import tour_catalog
from tests.conftest import default_tour_fields


def _update_fields(**overrides):
    fields = default_tour_fields(**overrides)
    del fields["id"]
    return fields


@pytest.mark.asyncio
async def test_create_tour_persists_and_returns_it(db_session):
    tour = await tour_catalog.create_tour(db_session, default_tour_fields())
    assert tour.id == "passeio-teste"
    assert (await tour_catalog.get_tour(db_session, "passeio-teste")).nome == "Passeio de teste"


@pytest.mark.asyncio
async def test_create_tour_duplicate_id_raises_already_exists(db_session):
    await tour_catalog.create_tour(db_session, default_tour_fields())
    duplicate = default_tour_fields(nome="Outro nome")

    with pytest.raises(tour_catalog.TourAlreadyExistsError):
        await tour_catalog.create_tour(db_session, duplicate)


@pytest.mark.asyncio
async def test_get_tour_unknown_id_raises_not_found(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.get_tour(db_session, "nao-existe")


@pytest.mark.asyncio
async def test_update_tour_replaces_fields(db_session):
    await tour_catalog.create_tour(db_session, default_tour_fields())
    updated = await tour_catalog.update_tour(
        db_session, "passeio-teste", _update_fields(preco_reais=150.0)
    )
    assert updated.preco_reais == 150.0


@pytest.mark.asyncio
async def test_update_tour_unknown_id_raises_not_found(db_session):
    fields = _update_fields()

    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.update_tour(db_session, "nao-existe", fields)


@pytest.mark.asyncio
async def test_deactivate_tour_sets_ativo_false_without_deleting(db_session):
    await tour_catalog.create_tour(db_session, default_tour_fields())
    deactivated = await tour_catalog.deactivate_tour(db_session, "passeio-teste")
    assert deactivated.ativo is False
    assert await tour_catalog.get_tour(db_session, "passeio-teste")


@pytest.mark.asyncio
async def test_deactivate_tour_unknown_id_raises_not_found(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.deactivate_tour(db_session, "nao-existe")


@pytest.mark.asyncio
async def test_list_tours_filters_inactive_by_default(db_session):
    await tour_catalog.create_tour(db_session, default_tour_fields())
    await tour_catalog.create_tour(
        db_session, default_tour_fields(id="passeio-inativo", ativo=False)
    )

    active_only = await tour_catalog.list_tours(db_session, incluir_inativos=False)
    all_tours = await tour_catalog.list_tours(db_session, incluir_inativos=True)

    assert [t.id for t in active_only] == ["passeio-teste"]
    assert {t.id for t in all_tours} == {"passeio-teste", "passeio-inativo"}
