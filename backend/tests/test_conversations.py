from datetime import UTC, datetime

import pytest

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.services import groq_client


async def _create_conversation_with_messages(db_session, phone):
    conversation = Conversation(whatsapp_phone=phone, status=ConversationStatus.ABERTA)
    db_session.add(conversation)
    await db_session.flush()
    db_session.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.ENTRADA,
            tipo=MessageType.TEXTO,
            conteudo="oi",
        )
    )
    await db_session.commit()
    return conversation


@pytest.mark.asyncio
async def test_list_conversations_returns_empty_when_none(client):
    response = await client.get("/api/conversations")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_conversations_returns_created_conversations(client, db_session):
    await _create_conversation_with_messages(db_session, "5598911112222")

    response = await client.get("/api/conversations")

    assert response.status_code == 200
    [summary] = response.json()
    assert summary["whatsapp_phone"] == "5598911112222"
    assert summary["status"] == "aberta"


@pytest.mark.asyncio
async def test_list_conversations_unauthenticated_returns_401(client):
    response = await client.get("/api/conversations", headers={"Authorization": ""})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_conversation_returns_detail_with_messages(client, db_session):
    conversation = await _create_conversation_with_messages(db_session, "5598999997777")

    response = await client.get(f"/api/conversations/{conversation.id}")
    assert response.status_code == 200
    body = response.json()
    assert [m["conteudo"] for m in body["messages"]] == ["oi"]


@pytest.mark.asyncio
async def test_get_unknown_conversation_returns_404(client):
    response = await client.get("/api/conversations/nao-existe")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_conversation_unauthenticated_returns_401(client, db_session):
    conversation = await _create_conversation_with_messages(db_session, "5598999996666")

    response = await client.get(
        f"/api/conversations/{conversation.id}", headers={"Authorization": ""}
    )
    assert response.status_code == 401


async def _create_conversation(db_session, phone, status):
    conversation = Conversation(whatsapp_phone=phone, status=status)
    db_session.add(conversation)
    await db_session.commit()
    return conversation


@pytest.mark.asyncio
@pytest.mark.parametrize("target", list(ConversationStatus))
@pytest.mark.parametrize("initial", list(ConversationStatus))
async def test_change_status_accepts_any_status_from_any_origin(
    client, db_session, initial, target
):
    """Inclui reabrir (`resolvida -> aberta`) e repetir o mesmo status (idempotente)."""
    conversation = await _create_conversation(db_session, "5598900001001", initial)

    response = await client.patch(
        f"/api/conversations/{conversation.id}/status", json={"status": target.value}
    )

    assert response.status_code == 200
    assert response.json()["status"] == target.value
    assert response.json()["id"] == conversation.id
    detail = await client.get(f"/api/conversations/{conversation.id}")
    assert detail.json()["status"] == target.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [{"status": "qualquer-coisa"}, {"status": "RESOLVIDA"}, {"status": None}, {"status": 1}, {}],
    ids=["invalid", "wrong-case", "null", "number", "missing"],
)
async def test_change_status_rejects_values_that_are_not_a_status(client, db_session, body):
    conversation = await _create_conversation(
        db_session, "5598900001003", ConversationStatus.PRECISA_ATENCAO
    )

    response = await client.patch(f"/api/conversations/{conversation.id}/status", json=body)

    assert response.status_code == 422
    detail = await client.get(f"/api/conversations/{conversation.id}")
    assert detail.json()["status"] == "precisa_atencao"


@pytest.mark.asyncio
async def test_resolve_unknown_conversation_returns_404(client):
    response = await client.patch(
        "/api/conversations/nao-existe/status", json={"status": "resolvida"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resolve_conversation_unauthenticated_returns_401(client, db_session):
    conversation = await _create_conversation(
        db_session, "5598900001004", ConversationStatus.ABERTA
    )

    response = await client.patch(
        f"/api/conversations/{conversation.id}/status",
        json={"status": "resolvida"},
        headers={"Authorization": ""},
    )

    assert response.status_code == 401
    detail = await client.get(f"/api/conversations/{conversation.id}")
    assert detail.json()["status"] == "aberta"


@pytest.mark.asyncio
async def test_list_puts_resolved_conversations_after_the_pending_ones(client, db_session):
    pending = await _create_conversation(
        db_session, "5598900001006", ConversationStatus.PRECISA_ATENCAO
    )
    resolved = await _create_conversation(db_session, "5598900001005", ConversationStatus.ABERTA)
    # Resolvida DEPOIS: o `updated_at` dela fica mais novo que o da pendente. Só a regra de
    # "resolvidas por último" mantém a pendente no topo (a ordem por data sozinha inverteria).
    await client.patch(f"/api/conversations/{resolved.id}/status", json={"status": "resolvida"})

    listing = (await client.get("/api/conversations")).json()

    assert [c["id"] for c in listing] == [pending.id, resolved.id]


async def _add_message(db_session, conversation, text, minutes, direction=MessageDirection.ENTRADA):
    db_session.add(
        Message(
            conversation_id=conversation.id,
            direction=direction,
            tipo=MessageType.AUDIO_TRANSCRITO,
            conteudo=text,
            created_at=datetime(2026, 9, 28, 9, minutes, tzinfo=UTC),
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_list_includes_the_last_message_preview_of_each_conversation(client, db_session):
    first = await _create_conversation(db_session, "5598900002001", ConversationStatus.ABERTA)
    second = await _create_conversation(db_session, "5598900002002", ConversationStatus.ABERTA)
    await _add_message(db_session, first, "primeira", 1)
    await _add_message(db_session, first, "mais recente", 5, MessageDirection.SAIDA)
    await _add_message(db_session, first, "intermediária", 3)
    await _add_message(db_session, second, "de outra conversa", 2)

    listing = {c["id"]: c for c in (await client.get("/api/conversations")).json()}

    last = listing[first.id]["ultima_mensagem"]
    assert last["conteudo"] == "mais recente"
    assert last["direction"] == "saida"
    assert last["tipo"] == "audio_transcrito"
    assert last["created_at"].startswith("2026-09-28T09:05")
    assert listing[second.id]["ultima_mensagem"]["conteudo"] == "de outra conversa"


@pytest.mark.asyncio
async def test_list_returns_null_preview_for_a_conversation_without_messages(client, db_session):
    await _create_conversation(db_session, "5598900002003", ConversationStatus.ABERTA)

    [summary] = (await client.get("/api/conversations")).json()

    assert summary["ultima_mensagem"] is None


@pytest.mark.asyncio
async def test_list_and_detail_expose_when_the_conversation_started(client, db_session):
    conversation = await _create_conversation(
        db_session, "5598900002004", ConversationStatus.ABERTA
    )

    [summary] = (await client.get("/api/conversations")).json()
    detail = (await client.get(f"/api/conversations/{conversation.id}")).json()

    assert summary["created_at"] == detail["created_at"] == conversation.created_at.isoformat()


@pytest.mark.asyncio
async def test_preview_is_truncated_to_200_characters(client, db_session):
    conversation = await _create_conversation(
        db_session, "5598900002005", ConversationStatus.ABERTA
    )
    await _add_message(db_session, conversation, "ã" * 500, 1)

    [summary] = (await client.get("/api/conversations")).json()

    assert summary["ultima_mensagem"]["conteudo"] == "ã" * 200


@pytest.mark.asyncio
async def test_preview_breaks_a_created_at_tie_by_the_highest_message_id(client, db_session):
    conversation = await _create_conversation(
        db_session, "5598900002006", ConversationStatus.ABERTA
    )
    same_instant = datetime(2026, 9, 28, 9, 30, tzinfo=UTC)
    for message_id, text in (("m-a", "empate A"), ("m-b", "empate B")):
        db_session.add(
            Message(
                id=message_id,
                conversation_id=conversation.id,
                direction=MessageDirection.ENTRADA,
                tipo=MessageType.TEXTO,
                conteudo=text,
                created_at=same_instant,
            )
        )
    await db_session.commit()

    [summary] = (await client.get("/api/conversations")).json()

    assert summary["ultima_mensagem"]["conteudo"] == "empate B"


@pytest.mark.asyncio
async def test_timestamps_are_always_serialized_as_utc(client, db_session):
    """O SQLite devolve datas sem fuso; o navegador leria como hora local e deslocaria tudo."""
    conversation = await _create_conversation(
        db_session, "5598900002007", ConversationStatus.ABERTA
    )
    await _add_message(db_session, conversation, "oi", 5)
    db_session.expire_all()

    [summary] = (await client.get("/api/conversations")).json()
    detail = (await client.get(f"/api/conversations/{conversation.id}")).json()

    stamps = [
        summary["created_at"],
        summary["updated_at"],
        summary["ultima_mensagem"]["created_at"],
        detail["messages"][0]["created_at"],
    ]
    assert all(stamp.endswith("+00:00") for stamp in stamps)
    assert summary["ultima_mensagem"]["created_at"] == "2026-09-28T09:05:00+00:00"


async def _suggesting_conversation(db_session, sample_tours, phone, active=True):
    """Conversa cujo último passeio sugerido é o primeiro do catálogo de exemplo."""
    sample_tours[0].ativo = active
    db_session.add_all(sample_tours)
    conversation = await _create_conversation(db_session, phone, ConversationStatus.ABERTA)
    conversation.passeio_sugerido_id = "passeio-bugre-orla"
    await db_session.commit()
    # Sem isso o Tour ficaria no mapa de identidade da sessão compartilhada com o app e um
    # relacionamento não carregado (sem `selectinload`) passaria despercebido.
    db_session.expunge_all()
    return conversation


@pytest.mark.asyncio
async def test_detail_includes_the_suggested_tour(client, db_session, sample_tours):
    conversation = await _suggesting_conversation(db_session, sample_tours, "5598900004001")

    detail = (await client.get(f"/api/conversations/{conversation.id}")).json()

    tour = detail["passeio_sugerido"]
    assert tour["id"] == "passeio-bugre-orla"
    assert tour["nome"] == "Passeio de bugre pela orla"
    assert tour["acessivel_cadeirantes"] is True
    assert tour["preco_reais"] == 100


@pytest.mark.asyncio
async def test_detail_without_a_suggestion_returns_null(client, db_session):
    conversation = await _create_conversation(
        db_session, "5598900004002", ConversationStatus.ABERTA
    )

    detail = (await client.get(f"/api/conversations/{conversation.id}")).json()

    assert detail["passeio_sugerido"] is None


@pytest.mark.asyncio
async def test_detail_still_shows_a_suggested_tour_that_was_deactivated(
    client, db_session, sample_tours
):
    conversation = await _suggesting_conversation(
        db_session, sample_tours, "5598900004003", active=False
    )

    detail = (await client.get(f"/api/conversations/{conversation.id}")).json()

    assert detail["passeio_sugerido"]["id"] == "passeio-bugre-orla"


async def _translate(client, *, texto="Olá!", idioma_destino="en", headers=None):
    return await client.post(
        "/api/conversations/traducao",
        json={"texto": texto, "idioma_destino": idioma_destino},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_translate_message_returns_the_translation(client, monkeypatch):
    captured = {}

    async def fake_translate_text(settings, texto, idioma_destino):
        captured["texto"] = texto
        captured["idioma_destino"] = idioma_destino
        return "Hello!"

    monkeypatch.setattr(groq_client, "translate_text", fake_translate_text)

    response = await _translate(client)

    assert response.status_code == 200
    assert response.json() == {"traducao": "Hello!"}
    assert captured == {"texto": "Olá!", "idioma_destino": "en"}


@pytest.mark.asyncio
async def test_translate_message_rejects_an_unsupported_target_language(client):
    assert (await _translate(client, idioma_destino="fr")).status_code == 422


@pytest.mark.asyncio
async def test_translate_message_rejects_empty_text(client):
    assert (await _translate(client, texto="   ")).status_code == 422


@pytest.mark.asyncio
async def test_translate_message_returns_503_when_groq_is_unavailable(client, monkeypatch):
    async def failing_translate_text(settings, texto, idioma_destino):
        raise groq_client.GroqUnavailableError("ReadTimeout")

    monkeypatch.setattr(groq_client, "translate_text", failing_translate_text)

    assert (await _translate(client)).status_code == 503


@pytest.mark.asyncio
async def test_translate_message_unauthenticated_returns_401(client):
    response = await _translate(client, headers={"Authorization": ""})

    assert response.status_code == 401
