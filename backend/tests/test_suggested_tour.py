import json
import logging

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.conversation import ConversationStatus
from app.models.message import Message
from app.services import message_handler, whatsapp_client
from app.services.groq_client import GroqUnavailableError, parse_reply
from app.services.message_handler import IncomingMessage, process_incoming_message


def _reply_suggesting(tour_id, **extra):
    """Groq falso cuja saída passa pelo mesmo parser da produção."""
    payload = {"resposta": "Recomendo!", "passeio_sugerido_id": tour_id, **extra}

    async def fake_ask_groq(settings, system_prompt, user_message):
        return parse_reply(json.dumps(payload))

    return fake_ask_groq


async def _chat(db_session, sample_tours, monkeypatch, text, ask):
    db_session.add_all(sample_tours)
    await db_session.commit()
    monkeypatch.setattr(whatsapp_client, "send_text_message", _noop_send)
    monkeypatch.setattr(message_handler, "ask_groq", ask)
    return await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900003001", "text", text)
    )


async def _noop_send(settings, to, body):
    return None


@pytest.mark.asyncio
async def test_suggested_tour_is_saved_on_the_conversation(db_session, sample_tours, monkeypatch):
    conversation = await _chat(
        db_session, sample_tours, monkeypatch, "oi", _reply_suggesting("passeio-bugre-orla")
    )

    assert conversation is not None
    assert conversation.passeio_sugerido_id == "passeio-bugre-orla"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hostile_id",
    ["nao-existe", "'; DROP TABLE tours;--", "<script>alert(1)</script>", "trilha-das-emendas"],
    ids=["unknown", "sql", "html", "real-tour-that-was-not-offered"],
)
async def test_suggested_tour_outside_the_candidates_is_discarded(
    db_session, sample_tours, monkeypatch, hostile_id
):
    # "cadeirante" deixa só o passeio acessível como candidato; nenhum dos ids acima está nele.
    conversation = await _chat(
        db_session,
        sample_tours,
        monkeypatch,
        "tenho um cadeirante no grupo",
        _reply_suggesting(hostile_id),
    )

    assert conversation is not None
    assert conversation.passeio_sugerido_id is None


@pytest.mark.asyncio
async def test_a_later_reply_without_suggestion_keeps_the_previous_one(
    db_session, sample_tours, monkeypatch
):
    first = await _chat(
        db_session, sample_tours, monkeypatch, "oi", _reply_suggesting("rio-preguicas")
    )
    monkeypatch.setattr(message_handler, "ask_groq", _reply_suggesting(None))

    again = await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900003001", "text", "e o preço?")
    )

    assert first is not None
    assert again is not None
    assert again.id == first.id
    assert again.passeio_sugerido_id == "rio-preguicas"


@pytest.mark.asyncio
async def test_a_new_valid_suggestion_replaces_the_previous_one(
    db_session, sample_tours, monkeypatch
):
    await _chat(db_session, sample_tours, monkeypatch, "oi", _reply_suggesting("rio-preguicas"))
    monkeypatch.setattr(message_handler, "ask_groq", _reply_suggesting("trilha-das-emendas"))

    conversation = await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900003001", "text", "e outro?")
    )

    assert conversation is not None
    assert conversation.passeio_sugerido_id == "trilha-das-emendas"


@pytest.mark.asyncio
async def test_unexpected_model_fields_change_nothing(db_session, sample_tours, monkeypatch):
    ask = _reply_suggesting(None, status="resolvida", precisa_atencao_humana=False, acao="apagar")

    conversation = await _chat(db_session, sample_tours, monkeypatch, "oi", ask)

    assert conversation is not None
    assert conversation.status == ConversationStatus.ABERTA
    assert conversation.passeio_sugerido_id is None


@pytest.mark.asyncio
async def test_groq_receives_no_phone_number(db_session, sample_tours, monkeypatch):
    seen = []

    async def spy_ask_groq(settings, system_prompt, user_message):
        seen.append(system_prompt + user_message)
        return parse_reply(json.dumps({"resposta": "ok"}))

    await _chat(db_session, sample_tours, monkeypatch, "oi, tudo bem?", spy_ask_groq)

    assert seen
    assert "5598900003001" not in seen[0]


def _groq_down(error_type):
    async def ask(settings, system_prompt, user_message):
        raise error_type

    return ask


async def _groq_outage(db_session, sample_tours, monkeypatch):
    """Catálogo no banco, WhatsApp falso que guarda o que foi enviado e Groq fora do ar."""
    sent = []

    async def capture_send(settings, to, body):
        sent.append(body)

    db_session.add_all(sample_tours)
    await db_session.commit()
    monkeypatch.setattr(whatsapp_client, "send_text_message", capture_send)
    monkeypatch.setattr(message_handler, "ask_groq", _groq_down(GroqUnavailableError()))
    return sent


@pytest.mark.asyncio
async def test_groq_outage_sends_a_fallback_and_asks_for_a_human(
    db_session, sample_tours, monkeypatch
):
    sent = await _groq_outage(db_session, sample_tours, monkeypatch)

    conversation = await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900006001", "text", "oi")
    )

    assert conversation is not None
    assert sent == [message_handler.GROQ_FALLBACK_REPLY]
    assert conversation.status == ConversationStatus.PRECISA_ATENCAO
    assert conversation.passeio_sugerido_id is None
    stored = await db_session.execute(select(Message.conteudo).order_by(Message.created_at))
    assert list(stored.scalars().all()) == ["oi", message_handler.GROQ_FALLBACK_REPLY]


@pytest.mark.asyncio
async def test_webhook_answers_200_when_groq_is_down(client, sample_tours, db_session, monkeypatch):
    sent = await _groq_outage(db_session, sample_tours, monkeypatch)
    message = {"from": "5598900006002", "type": "text", "text": {"body": "oi"}, "id": "wamid.fora"}
    payload = {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}

    response = await client.post("/webhook/whatsapp", json=payload)

    assert response.status_code == 200
    assert sent == [message_handler.GROQ_FALLBACK_REPLY]
    [summary] = (await client.get("/api/conversations")).json()
    assert summary["status"] == "precisa_atencao"


async def _outage_log(db_session, sample_tours, monkeypatch, caplog, error, phone):
    """Processa uma mensagem com o Groq falhando por `error` e devolve o aviso de contingência."""
    await _groq_outage(db_session, sample_tours, monkeypatch)
    monkeypatch.setattr(message_handler, "ask_groq", _groq_down(error))
    with caplog.at_level(logging.WARNING, logger=message_handler.logger.name):
        await process_incoming_message(
            db_session, get_settings(), IncomingMessage(phone, "text", "oi")
        )
    return next(r for r in caplog.records if "Groq indisponível" in r.getMessage())


@pytest.mark.asyncio
async def test_groq_outage_logs_the_cause_without_personal_data(
    db_session, sample_tours, monkeypatch, caplog
):
    record = await _outage_log(
        db_session,
        sample_tours,
        monkeypatch,
        caplog,
        GroqUnavailableError("ReadTimeout", None),
        "5598900006003",
    )

    assert record.motivo == "groq"
    assert record.causa == "ReadTimeout"
    assert record.status_http is None
    # O formato padrão de log descarta o `extra`: a causa também precisa estar no texto lido.
    assert "causa=ReadTimeout" in record.getMessage()
    assert "status_http=None" in record.getMessage()
    assert "5598900006003" not in caplog.text


@pytest.mark.asyncio
async def test_groq_outage_log_text_tells_a_wrong_key_from_an_outage(
    db_session, sample_tours, monkeypatch, caplog
):
    await _outage_log(
        db_session,
        sample_tours,
        monkeypatch,
        caplog,
        GroqUnavailableError("HTTPStatusError", 401),
        "5598900006005",
    )

    assert "causa=HTTPStatusError status_http=401" in caplog.text


@pytest.mark.asyncio
async def test_groq_outage_does_not_invent_or_erase_the_language(
    db_session, sample_tours, monkeypatch
):
    await _groq_outage(db_session, sample_tours, monkeypatch)
    incoming = IncomingMessage("5598900006004", "text", "oi")

    fresh = await process_incoming_message(db_session, get_settings(), incoming)
    assert fresh is not None
    assert fresh.idioma_detectado is None
    assert await _outbound_language(db_session) is None

    fresh.idioma_detectado = "en"
    await db_session.commit()
    again = await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900006004", "text", "hello?")
    )

    assert again is not None
    assert again.id == fresh.id
    assert again.idioma_detectado == "en"


async def _outbound_language(db_session):
    result = await db_session.execute(
        select(Message.idioma).where(Message.direction == "saida").order_by(Message.created_at)
    )
    return result.scalars().first()


@pytest.mark.asyncio
async def test_a_reply_without_a_suggestion_does_not_log_a_discard(
    db_session, sample_tours, monkeypatch, caplog
):
    with caplog.at_level(logging.WARNING, logger=message_handler.logger.name):
        await _chat(db_session, sample_tours, monkeypatch, "oi", _reply_suggesting(None))

    assert "fora dos candidatos" not in caplog.text


@pytest.mark.asyncio
async def test_discarding_a_suggestion_logs_the_reason_without_the_id(
    db_session, sample_tours, monkeypatch, caplog
):
    with caplog.at_level(logging.WARNING, logger=message_handler.logger.name):
        await _chat(db_session, sample_tours, monkeypatch, "oi", _reply_suggesting("nao-existe"))

    record = next(r for r in caplog.records if "fora dos candidatos" in r.getMessage())
    assert record.motivo == "allowlist"
    assert "nao-existe" not in caplog.text
