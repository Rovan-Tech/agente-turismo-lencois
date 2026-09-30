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
