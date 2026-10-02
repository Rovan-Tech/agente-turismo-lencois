import pytest

from tests.conftest import persist


def _booking_payload(**overrides):
    payload = {
        "data": "2026-09-28",
        "pessoas": 3,
        "forma_pagamento": "pix",
        "telefone": "5598999998888",
    }
    payload.update(overrides)
    return payload


async def _paid_booking_on_sample_tour(client, db_session, sample_tours):
    """Persiste `sample_tours[0]` e cria um agendamento pago em 2026-09-28 para ele."""
    await persist(db_session, sample_tours[0])
    await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=_booking_payload())


async def _persist_inactive_sample_tour(db_session, sample_tours):
    """Persiste `sample_tours[0]` (id `passeio-bugre-orla`) já desativado."""
    inactive = sample_tours[0]
    inactive.ativo = False
    await persist(db_session, inactive)


async def _get_day_bookings(client, data="2026-09-28"):
    return await client.get("/api/tours/passeio-bugre-orla/agendamentos", params={"data": data})


@pytest.mark.asyncio
async def test_get_agenda_returns_occupancy_for_every_day_of_month(
    client, db_session, sample_tours
):
    await _paid_booking_on_sample_tour(client, db_session, sample_tours)

    response = await client.get("/api/tours/passeio-bugre-orla/agenda", params={"mes": "2026-09"})

    assert response.status_code == 200
    days = {d["data"]: d for d in response.json()}
    assert len(days) == 30
    assert days["2026-09-28"]["ocupadas"] == 3


@pytest.mark.asyncio
async def test_get_agenda_unknown_tour_returns_404(client):
    response = await client.get("/api/tours/nao-existe/agenda", params={"mes": "2026-09"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agenda_inactive_tour_returns_404(client, db_session, sample_tours):
    await _persist_inactive_sample_tour(db_session, sample_tours)

    response = await client.get("/api/tours/passeio-bugre-orla/agenda", params={"mes": "2026-09"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "mes", ["2026-9", "2026/09", "setembro-2026", "2026-13", "2026-00", "0000-09", ""]
)
@pytest.mark.asyncio
async def test_get_agenda_invalid_mes_returns_422(client, db_session, sample_tours, mes):
    await persist(db_session, sample_tours[0])

    response = await client.get("/api/tours/passeio-bugre-orla/agenda", params={"mes": mes})

    assert response.status_code == 422
    # Mesmo shape do 422 nativo do FastAPI (`detail` é lista de `ValidationError`, não string) —
    # é o que o OpenAPI documenta pra esse status em toda rota, e o schemathesis prova no CI.
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "mes"]


@pytest.mark.asyncio
async def test_list_day_bookings_returns_only_paid(client, db_session, sample_tours):
    await _paid_booking_on_sample_tour(client, db_session, sample_tours)

    response = await _get_day_bookings(client)

    assert response.status_code == 200
    [booking] = response.json()
    assert booking["status_pagamento"] == "pago"
    assert booking["pessoas"] == 3


@pytest.mark.asyncio
async def test_list_day_bookings_invalid_data_returns_422(client, db_session, sample_tours):
    await persist(db_session, sample_tours[0])

    response = await client.get(
        "/api/tours/passeio-bugre-orla/agendamentos", params={"data": "28-09-2026"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_day_bookings_unknown_tour_returns_404(client):
    response = await client.get("/api/tours/nao-existe/agendamentos", params={"data": "2026-09-28"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_day_bookings_inactive_tour_returns_404(client, db_session, sample_tours):
    await _persist_inactive_sample_tour(db_session, sample_tours)

    response = await _get_day_bookings(client)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_booking_valid_payload_returns_201_as_paid(client, db_session, sample_tours):
    await persist(db_session, sample_tours[0])

    response = await client.post(
        "/api/tours/passeio-bugre-orla/agendamentos", json=_booking_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status_pagamento"] == "pago"
    assert body["ocupadas"] == 3
    assert body["capacidade"] == 30


@pytest.mark.asyncio
async def test_create_booking_decrements_remaining_seats_across_requests(
    client, db_session, sample_tours
):
    sample_tours[0].capacidade_diaria = 5
    await persist(db_session, sample_tours[0])

    first = await client.post(
        "/api/tours/passeio-bugre-orla/agendamentos", json=_booking_payload(pessoas=4)
    )
    assert first.status_code == 201
    assert first.json()["ocupadas"] == 4

    second = await client.post(
        "/api/tours/passeio-bugre-orla/agendamentos", json=_booking_payload(pessoas=2)
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_booking_unknown_tour_returns_404(client):
    response = await client.post("/api/tours/nao-existe/agendamentos", json=_booking_payload())
    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"pessoas": 0},
        {"pessoas": -1},
        {"pessoas": 51},
        {"status_pagamento": "pago"},
        {"forma_pagamento": "dinheiro"},
        {"data": "28-09-2026"},
        {"telefone": "abc"},
        {"telefone": "1" * 40},
    ],
    ids=[
        "pessoas-zero",
        "pessoas-negativo",
        "pessoas-acima-do-teto",
        "campo-desconhecido",
        "forma-pagamento-invalida",
        "data-invalida",
        "telefone-nao-numerico",
        "telefone-acima-do-teto",
    ],
)
@pytest.mark.asyncio
async def test_create_booking_rejects_invalid_payloads(client, db_session, sample_tours, overrides):
    await persist(db_session, sample_tours[0])

    payload = _booking_payload(**overrides)
    response = await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_booking_accepts_missing_optional_phone(client, db_session, sample_tours):
    await persist(db_session, sample_tours[0])
    payload = _booking_payload()
    del payload["telefone"]

    response = await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=payload)
    assert response.status_code == 201
    assert response.json()["telefone"] is None


@pytest.mark.parametrize("forma_pagamento", ["pix", "boleto", "cartao"])
@pytest.mark.asyncio
async def test_create_booking_always_persists_as_paid(
    client, db_session, sample_tours, forma_pagamento
):
    await persist(db_session, sample_tours[0])

    payload = _booking_payload(forma_pagamento=forma_pagamento)
    response = await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=payload)
    assert response.json()["status_pagamento"] == "pago"


@pytest.mark.asyncio
async def test_create_booking_does_not_mutate_tour_fields(client, db_session, sample_tours):
    await persist(db_session, sample_tours[0])

    await client.post("/api/tours/passeio-bugre-orla/agendamentos", json=_booking_payload())

    tours = (await client.get("/api/tours")).json()
    [tour] = [t for t in tours if t["id"] == "passeio-bugre-orla"]
    assert tour["nome"] == sample_tours[0].nome
    assert tour["preco_reais"] == sample_tours[0].preco_reais
    assert tour["ativo"] is True
