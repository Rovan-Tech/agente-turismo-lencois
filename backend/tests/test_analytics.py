from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.models.booking import Booking, PaymentMethod, PaymentStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageAuthor, MessageDirection
from app.models.tour import Tour
from app.services import analytics
from tests.conftest import default_tour_fields, persist

NOW = datetime.now(UTC)


async def _compute(db_session: Any, period_days: int) -> dict[str, Any]:
    """`compute_analytics`, com o resultado tipado como `Any` pro teste poder indexar à vontade."""
    return cast("dict[str, Any]", await analytics.compute_analytics(db_session, period_days))


def _conv(
    phone: str,
    *,
    status: ConversationStatus = ConversationStatus.ABERTA,
    idioma: str | None = "pt",
    ago: timedelta = timedelta(hours=1),
) -> Conversation:
    return Conversation(
        whatsapp_phone=phone, status=status, idioma_detectado=idioma, created_at=NOW - ago
    )


def _msg(
    conversation: Conversation,
    autor: MessageAuthor,
    *,
    ago: timedelta,
    autor_sub: str | None = None,
    direction: MessageDirection = MessageDirection.ENTRADA,
) -> Message:
    return Message(
        conversation_id=conversation.id,
        direction=direction,
        autor=autor,
        autor_sub=autor_sub,
        conteudo="oi",
        created_at=NOW - ago,
    )


def _human_reply(conversation: Conversation, *, ago: timedelta, autor_sub: str) -> Message:
    """Mensagem de saída de um atendente humano (a resposta que fecha o tempo de 1ª resposta)."""
    return _msg(
        conversation,
        MessageAuthor.ATENDENTE,
        ago=ago,
        autor_sub=autor_sub,
        direction=MessageDirection.SAIDA,
    )


def _booking(
    phone: str, *, status: PaymentStatus = PaymentStatus.PAGO, pessoas: int = 2
) -> Booking:
    return Booking(
        tour_id="passeio-teste",
        data=(NOW - timedelta(hours=1)).date(),
        pessoas=pessoas,
        forma_pagamento=PaymentMethod.PIX,
        status_pagamento=status,
        telefone=phone,
    )


@pytest.mark.asyncio
async def test_compute_analytics_rejects_an_unsupported_period(db_session):
    with pytest.raises(analytics.InvalidPeriodError):
        await analytics.compute_analytics(db_session, 14)


@pytest.mark.asyncio
async def test_compute_analytics_with_no_data_is_all_zero(db_session):
    result = await _compute(db_session, 7)

    assert result["atual"] == {
        "conversas": 0,
        "vendas": 0,
        "taxa_conversao_pct": 0.0,
        "resolvidas_so_ia_pct": 0.0,
        "primeira_resposta_humana_min": None,
    }
    assert result["destinos"] == []
    assert result["mapa_calor"]["valores"] == [[0] * 6 for _ in range(7)]


@pytest.mark.asyncio
async def test_a_paid_booking_counts_the_conversation_as_a_sale(db_session):
    conversation = _conv("5598900000001")
    await persist(db_session, conversation, _booking("5598900000001"))

    result = await _compute(db_session, 7)

    assert result["atual"]["vendas"] == 1
    assert result["destinos"] == [
        {"rotulo": "Virou venda", "quantidade": 1, "percentual": 100.0, "sub": None}
    ]


@pytest.mark.asyncio
async def test_a_pending_booking_counts_as_created_but_not_paid(db_session):
    pendente = _booking("5598900000002", status=PaymentStatus.PENDENTE)
    await persist(db_session, _conv("5598900000002"), pendente)

    result = await _compute(db_session, 7)

    assert result["atual"]["vendas"] == 0
    [destino] = result["destinos"]
    assert destino["rotulo"] == "Reserva criada, não paga"


@pytest.mark.asyncio
async def test_a_resolved_conversation_without_a_booking_has_no_sale(db_session):
    await persist(db_session, _conv("5598900000003", status=ConversationStatus.RESOLVIDA))

    result = await _compute(db_session, 7)

    [destino] = result["destinos"]
    assert destino["rotulo"] == "Resolvida, sem reserva"


@pytest.mark.asyncio
async def test_an_open_conversation_without_a_booking_is_in_progress(db_session):
    await persist(db_session, _conv("5598900000004", status=ConversationStatus.ABERTA))

    result = await _compute(db_session, 7)

    [destino] = result["destinos"]
    assert destino["rotulo"] == "Em andamento"


@pytest.mark.asyncio
async def test_quem_atendeu_splits_ai_only_from_human_assisted(db_session):
    ia_only = _conv("5598900000005")
    with_human = _conv("5598900000006")
    await persist(db_session, ia_only, with_human)
    await persist(db_session, _human_reply(with_human, ago=timedelta(minutes=5), autor_sub="p1"))

    result = await _compute(db_session, 7)

    assert result["quem_atendeu"] == [
        {"rotulo": "Só a IA", "quantidade": 1, "percentual": 50.0, "sub": None},
        {"rotulo": "Com apoio humano", "quantidade": 1, "percentual": 50.0, "sub": None},
    ]
    assert result["atual"]["resolvidas_so_ia_pct"] == 50.0


@pytest.mark.asyncio
async def test_first_human_reply_is_the_median_gap_after_the_tourists_last_message(db_session):
    conversation = _conv("5598900000007")
    await persist(db_session, conversation)
    await persist(
        db_session,
        _msg(conversation, MessageAuthor.TURISTA, ago=timedelta(minutes=20)),
        _human_reply(conversation, ago=timedelta(minutes=10), autor_sub="p1"),
    )

    result = await _compute(db_session, 7)

    assert result["atual"]["primeira_resposta_humana_min"] == 10.0


@pytest.mark.asyncio
async def test_por_pessoa_groups_by_attendant_and_counts_their_sales(db_session):
    attended = _conv("5598900000008")
    await persist(db_session, attended, _booking("5598900000008"))
    await persist(
        db_session, _human_reply(attended, ago=timedelta(minutes=1), autor_sub="pessoa-1")
    )

    result = await _compute(db_session, 7)

    [row] = result["por_pessoa"]
    assert row["rotulo"] == "pessoa-1"
    assert row["quantidade"] == 1
    assert "1 vendas" in row["sub"]


@pytest.mark.asyncio
async def test_idiomas_groups_conversations_by_detected_language(db_session):
    await persist(
        db_session,
        _conv("5598900000009", idioma="pt"),
        _conv("5598900000010", idioma="en"),
        _conv("5598900000011", idioma="en"),
    )

    result = await _compute(db_session, 7)

    labels = {row["rotulo"]: row["quantidade"] for row in result["idiomas"]}
    assert labels == {"EN": 2, "PT": 1}


@pytest.mark.asyncio
async def test_tour_metrics_averages_occupancy_only_over_days_with_bookings(db_session):
    tour = Tour(**default_tour_fields(id="passeio-teste", capacidade_diaria=10))
    booking_today = _booking("5598900000012", pessoas=5)
    booking_yesterday = Booking(
        tour_id="passeio-teste",
        data=(NOW - timedelta(days=1)).date(),
        pessoas=10,
        forma_pagamento=PaymentMethod.PIX,
        status_pagamento=PaymentStatus.PAGO,
        telefone="5598900000013",
    )
    await persist(db_session, tour, booking_today, booking_yesterday)

    result = await _compute(db_session, 7)

    [row] = result["passeios"]
    assert row["quantidade"] == 15
    assert row["sub"] == "ocupação média de 75.0%"  # média entre 50% (hoje) e 100% (ontem)


@pytest.mark.asyncio
async def test_heatmap_buckets_by_the_agencys_local_weekday_and_hour(db_session):
    # 12:00 UTC numa quarta-feira = 09:00 em America/Fortaleza (UTC-3): faixa "9-12h", "qua". A
    # quarta mais recente (não hoje, pra não cair fora do período em dias de teste lentos) garante
    # que a data continua dentro dos últimos 90 dias não importa quando a suíte rode.
    days_since_wednesday = (NOW.weekday() - 2) % 7 or 7
    wednesday_noon_utc = (NOW - timedelta(days=days_since_wednesday)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    assert wednesday_noon_utc.weekday() == 2
    conversation = Conversation(whatsapp_phone="5598900000014", created_at=wednesday_noon_utc)
    await persist(db_session, conversation)

    result = await _compute(db_session, 90)

    assert result["mapa_calor"]["dias"][2] == "qua"
    assert result["mapa_calor"]["faixas"][1] == "9-12h"
    assert result["mapa_calor"]["valores"][2][1] == 1


@pytest.mark.asyncio
async def test_the_previous_period_is_the_same_length_right_before_the_current_one(db_session):
    await persist(
        db_session,
        _conv("5598900000015", ago=timedelta(days=3)),  # dentro dos últimos 7 dias
        _conv("5598900000016", ago=timedelta(days=10)),  # nos 7 dias anteriores a esses
        _conv("5598900000017", ago=timedelta(days=20)),  # fora dos dois períodos
    )

    result = await _compute(db_session, 7)

    assert result["atual"]["conversas"] == 1
    assert result["anterior"]["conversas"] == 1


@pytest.mark.asyncio
async def test_get_analytics_requires_authentication(client):
    response = await client.get("/api/analytics", headers={"Authorization": ""})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_analytics_rejects_an_invalid_period(client):
    response = await client.get("/api/analytics", params={"periodo_dias": 14})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_analytics_returns_the_computed_payload(client):
    response = await client.get("/api/analytics", params={"periodo_dias": 30})

    assert response.status_code == 200
    body = response.json()
    assert body["periodo_dias"] == 30
    assert body["periodos_disponiveis"] == [7, 30, 90]
