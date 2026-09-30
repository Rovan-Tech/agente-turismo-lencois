import json

import pytest


async def _persist(db_session, *tours):
    for tour in tours:
        db_session.add(tour)
    await db_session.commit()


def _valid_payload(**overrides):
    payload = {
        "id": "passeio-nascer-do-sol",
        "nome": "Passeio ao nascer do sol",
        "descricao": "Saída antes do amanhecer para ver o sol nascer sobre as dunas.",
        "dificuldade_fisica": "media",
        "caminhada_areia_minutos": 15,
        "acessivel_idosos": False,
        "acessivel_cadeirantes": False,
        "acessivel_criancas_pequenas": True,
        "duracao_horas": 3.0,
        "faixa_etaria_recomendada": "todas as idades",
        "preco_reais": 140.0,
        "ativo": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_list_tours_returns_only_active(client, db_session, sample_tours):
    sample_tours[1].ativo = False
    await _persist(db_session, *sample_tours)

    response = await client.get("/api/tours")
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert ids == {"passeio-bugre-orla", "rio-preguicas"}


@pytest.mark.asyncio
async def test_list_tours_incluir_inativos_returns_all(client, db_session, sample_tours):
    sample_tours[1].ativo = False
    await _persist(db_session, *sample_tours)

    response = await client.get("/api/tours", params={"incluir_inativos": "true"})
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert ids == {"passeio-bugre-orla", "trilha-das-emendas", "rio-preguicas"}


@pytest.mark.asyncio
async def test_create_tour_valid_payload_persists_and_returns_201(client, db_session):
    response = await client.post("/api/tours", json=_valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "passeio-nascer-do-sol"
    assert body["ativo"] is True
    assert body["preco_reais"] == 140.0

    listed = await client.get("/api/tours")
    assert "passeio-nascer-do-sol" in {t["id"] for t in listed.json()}


@pytest.mark.asyncio
async def test_create_tour_duplicate_id_returns_409(client):
    first = await client.post("/api/tours", json=_valid_payload())
    assert first.status_code == 201

    second = await client.post("/api/tours", json=_valid_payload(nome="Outro nome"))
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_tour_unauthenticated_returns_401(client):
    response = await client.post("/api/tours", json=_valid_payload(), headers={"Authorization": ""})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"preco_reais": -10},
        {"duracao_horas": 0},
        {"id": "Passeio Inválido!"},
        {"dificuldade_fisica": "extrema"},
        {"caminhada_areia_minutos": -1},
        {"nome": ""},
        {"nome": "   "},
        {"descricao": ""},
        {"faixa_etaria_recomendada": "   "},
        {"duracao_horas": 25},
        {"preco_reais": 100_000_000},
        {"caminhada_areia_minutos": 601},
    ],
    ids=[
        "preco-negativo",
        "duracao-zero",
        "id-invalido",
        "dificuldade-invalida",
        "minutos-negativos",
        "nome-vazio",
        "nome-so-espaco",
        "descricao-vazia",
        "faixa-etaria-so-espaco",
        "duracao-acima-do-teto",
        "preco-acima-do-teto",
        "minutos-acima-do-teto",
    ],
)
@pytest.mark.asyncio
async def test_create_tour_invalid_payload_returns_422(client, overrides):
    response = await client.post("/api/tours", json=_valid_payload(**overrides))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_tour_missing_required_field_returns_422(client):
    payload = _valid_payload()
    del payload["nome"]
    response = await client.post("/api/tours", json=payload)

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["loc"] == ["body", "nome"]
    assert error["type"] == "missing"


@pytest.mark.parametrize("field", ["duracao_horas", "preco_reais"])
@pytest.mark.asyncio
async def test_create_tour_rejects_infinite_numbers(client, field):
    payload = _valid_payload(**{field: float("inf")})
    body = json.dumps(payload)  # json.dumps permite Infinity; o pydantic deve rejeitar
    response = await client.post(
        "/api/tours", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["loc"] == ["body", field]
    assert error["input"] is None


@pytest.mark.asyncio
async def test_update_tour_valid_payload_persists_and_returns_200(client, db_session, sample_tours):
    await _persist(db_session, sample_tours[0])

    payload = _valid_payload(nome="Passeio de bugre pela orla (atualizado)")
    del payload["id"]
    response = await client.put("/api/tours/passeio-bugre-orla", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Passeio de bugre pela orla (atualizado)"
    assert body["preco_reais"] == 140.0


@pytest.mark.asyncio
async def test_update_tour_unknown_id_returns_404(client):
    payload = _valid_payload()
    del payload["id"]
    response = await client.put("/api/tours/nao-existe", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tour_invalid_payload_returns_422(client, db_session, sample_tours):
    await _persist(db_session, sample_tours[0])

    payload = _valid_payload(preco_reais=-5)
    del payload["id"]
    response = await client.put("/api/tours/passeio-bugre-orla", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_tour_unauthenticated_returns_401(client, db_session, sample_tours):
    await _persist(db_session, sample_tours[0])

    payload = _valid_payload()
    del payload["id"]
    response = await client.put(
        "/api/tours/passeio-bugre-orla", json=payload, headers={"Authorization": ""}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_tour_soft_deletes_and_keeps_record(client, db_session, sample_tours):
    await _persist(db_session, sample_tours[0])

    response = await client.delete("/api/tours/passeio-bugre-orla")
    assert response.status_code == 200
    assert response.json()["ativo"] is False

    listed = await client.get("/api/tours", params={"incluir_inativos": "true"})
    assert "passeio-bugre-orla" in {t["id"] for t in listed.json()}


@pytest.mark.asyncio
async def test_delete_tour_unknown_id_returns_404(client):
    response = await client.delete("/api/tours/nao-existe")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_tour_unauthenticated_returns_401(client, db_session, sample_tours):
    await _persist(db_session, sample_tours[0])

    response = await client.delete("/api/tours/passeio-bugre-orla", headers={"Authorization": ""})
    assert response.status_code == 401
