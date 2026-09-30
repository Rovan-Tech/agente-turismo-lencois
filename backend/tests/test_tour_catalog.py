import pytest

from app.services import tour_catalog


def _fields(**overrides):
    fields = {
        "id": "passeio-teste",
        "nome": "Passeio de teste",
        "descricao": "Descrição do passeio de teste.",
        "dificuldade_fisica": "media",
        "caminhada_areia_minutos": 10,
        "acessivel_idosos": False,
        "acessivel_cadeirantes": False,
        "acessivel_criancas_pequenas": False,
        "duracao_horas": 2.0,
        "faixa_etaria_recomendada": "todas as idades",
        "preco_reais": 90.0,
        "ativo": True,
    }
    fields.update(overrides)
    return fields


def _update_fields(**overrides):
    fields = _fields(**overrides)
    del fields["id"]
    return fields


@pytest.mark.asyncio
async def test_create_tour_persists_and_returns_it(db_session):
    tour = await tour_catalog.create_tour(db_session, _fields())
    assert tour.id == "passeio-teste"
    assert (await tour_catalog.get_tour(db_session, "passeio-teste")).nome == "Passeio de teste"


@pytest.mark.asyncio
async def test_create_tour_duplicate_id_raises_already_exists(db_session):
    await tour_catalog.create_tour(db_session, _fields())
    with pytest.raises(tour_catalog.TourAlreadyExistsError):
        await tour_catalog.create_tour(db_session, _fields(nome="Outro nome"))


@pytest.mark.asyncio
async def test_get_tour_unknown_id_raises_not_found(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.get_tour(db_session, "nao-existe")


@pytest.mark.asyncio
async def test_update_tour_replaces_fields(db_session):
    await tour_catalog.create_tour(db_session, _fields())
    updated = await tour_catalog.update_tour(
        db_session, "passeio-teste", _update_fields(preco_reais=150.0)
    )
    assert updated.preco_reais == 150.0


@pytest.mark.asyncio
async def test_update_tour_unknown_id_raises_not_found(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.update_tour(db_session, "nao-existe", _update_fields())


@pytest.mark.asyncio
async def test_deactivate_tour_sets_ativo_false_without_deleting(db_session):
    await tour_catalog.create_tour(db_session, _fields())
    deactivated = await tour_catalog.deactivate_tour(db_session, "passeio-teste")
    assert deactivated.ativo is False
    assert await tour_catalog.get_tour(db_session, "passeio-teste")


@pytest.mark.asyncio
async def test_deactivate_tour_unknown_id_raises_not_found(db_session):
    with pytest.raises(tour_catalog.TourNotFoundError):
        await tour_catalog.deactivate_tour(db_session, "nao-existe")


@pytest.mark.asyncio
async def test_list_tours_filters_inactive_by_default(db_session):
    await tour_catalog.create_tour(db_session, _fields())
    await tour_catalog.create_tour(db_session, _fields(id="passeio-inativo", ativo=False))

    active_only = await tour_catalog.list_tours(db_session, incluir_inativos=False)
    all_tours = await tour_catalog.list_tours(db_session, incluir_inativos=True)

    assert [t.id for t in active_only] == ["passeio-teste"]
    assert {t.id for t in all_tours} == {"passeio-teste", "passeio-inativo"}
