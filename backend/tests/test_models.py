from decimal import Decimal

import pytest

from app.models.tour import DifficultyLevel, Tour
from app.seed import TOURS


def _sample_tour(**overrides):
    defaults = {
        "id": "t1",
        "nome": "Tour",
        "descricao": "desc",
        "dificuldade_fisica": DifficultyLevel.BAIXA,
        "caminhada_areia_minutos": 5,
        "acessivel_idosos": True,
        "acessivel_cadeirantes": True,
        "acessivel_criancas_pequenas": True,
        "duracao_horas": 2.0,
        "faixa_etaria_recomendada": "todas as idades",
        "preco_reais": Decimal("100.00"),
        "ativo": True,
    }
    defaults.update(overrides)
    return Tour(**defaults)


def test_to_catalog_dict_returns_expected_fields():
    tour = _sample_tour()
    data = tour.to_catalog_dict()

    assert data["id"] == "t1"
    assert data["dificuldade_fisica"] == DifficultyLevel.BAIXA
    assert "ativo" not in data


def test_to_catalog_dict_converts_preco_reais_to_float():
    tour = _sample_tour(preco_reais=Decimal("199.90"))
    data = tour.to_catalog_dict()

    assert data["preco_reais"] == 199.90
    assert isinstance(data["preco_reais"], float)


def test_seed_tours_have_unique_ids():
    ids = [tour.id for tour in TOURS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("tour", TOURS, ids=[tour.id for tour in TOURS])
def test_seed_tour_has_valid_required_fields(tour):
    assert tour.id
    assert tour.nome
    assert tour.descricao
    assert tour.faixa_etaria_recomendada
    assert tour.duracao_horas > 0
    assert float(tour.preco_reais) >= 0
    assert tour.caminhada_areia_minutos >= 0
