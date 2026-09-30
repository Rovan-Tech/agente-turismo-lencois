import pytest

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType


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
@pytest.mark.parametrize("initial", list(ConversationStatus))
async def test_resolve_conversation_marks_it_resolved_and_persists(client, db_session, initial):
    """Inclui `resolvida -> resolvida`: repetir a ação é inofensivo (idempotente)."""
    conversation = await _create_conversation(db_session, "5598900001001", initial)

    response = await client.patch(
        f"/api/conversations/{conversation.id}/status", json={"status": "resolvida"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolvida"
    assert response.json()["id"] == conversation.id
    detail = await client.get(f"/api/conversations/{conversation.id}")
    assert detail.json()["status"] == "resolvida"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"status": "aberta"},
        {"status": "precisa_atencao"},
        {"status": "qualquer-coisa"},
        {"status": None},
        {},
    ],
    ids=["aberta", "precisa_atencao", "invalid", "null", "missing"],
)
async def test_manual_status_change_only_accepts_resolvida(client, db_session, body):
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
