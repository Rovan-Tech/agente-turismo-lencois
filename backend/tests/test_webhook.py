import pytest

from app.services import message_handler
from app.services.groq_client import GroqReply


def _patch_dependencies(monkeypatch, ask_groq_fn, send_text_fn):
    monkeypatch.setattr(message_handler.whatsapp_client, "send_text_message", send_text_fn)
    monkeypatch.setattr(message_handler, "ask_groq", ask_groq_fn)


def _text_payload(phone: str, body: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"from": phone, "type": "text", "text": {"body": body}}]
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_incoming_text_message_creates_conversation_and_replies(
    client, db_session, sample_tours, monkeypatch
):
    for tour in sample_tours:
        db_session.add(tour)
    await db_session.commit()

    sent_messages = []

    async def fake_send_text_message(settings, to, body):
        sent_messages.append((to, body))

    async def fake_ask_groq(settings, system_prompt, user_message):
        return GroqReply(idioma="pt", precisa_atencao_humana=False, resposta="Recomendo o bugre!")

    _patch_dependencies(monkeypatch, fake_ask_groq, fake_send_text_message)

    response = await client.post("/webhook/whatsapp", json=_text_payload("5598999998888", "oi"))

    assert response.status_code == 200
    assert sent_messages == [("5598999998888", "Recomendo o bugre!")]

    conversations = await client.get("/api/conversations")
    assert conversations.status_code == 200
    body = conversations.json()
    assert len(body) == 1
    assert body[0]["whatsapp_phone"] == "5598999998888"
    assert body[0]["status"] == "aberta"

    detail = await client.get(f"/api/conversations/{body[0]['id']}")
    contents = [m["conteudo"] for m in detail.json()["messages"]]
    assert contents == ["oi", "Recomendo o bugre!"]


@pytest.mark.asyncio
async def test_escalation_flag_marks_conversation_as_needing_attention(
    client, db_session, sample_tours, monkeypatch
):
    for tour in sample_tours:
        db_session.add(tour)
    await db_session.commit()

    async def fake_send_text_message(settings, to, body):
        return None

    async def fake_ask_groq(settings, system_prompt, user_message):
        return GroqReply(
            idioma="pt", precisa_atencao_humana=True, resposta="Vou chamar um atendente humano."
        )

    _patch_dependencies(monkeypatch, fake_ask_groq, fake_send_text_message)

    await client.post(
        "/webhook/whatsapp", json=_text_payload("5598999997777", "quero falar com humano")
    )

    conversations = (await client.get("/api/conversations")).json()
    assert conversations[0]["status"] == "precisa_atencao"


@pytest.mark.asyncio
async def test_webhook_ignores_messages_without_phone(client):
    incoming_message = {"type": "text", "text": {"body": "oi"}}
    payload = {"entry": [{"changes": [{"value": {"messages": [incoming_message]}}]}]}
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    conversations = (await client.get("/api/conversations")).json()
    assert conversations == []
