from pathlib import Path

import pytest
from sqlalchemy import select

import app.services.transcription as transcription_module
from app.core.config import get_settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageType
from app.services import message_handler, whatsapp_client
from app.services.groq_client import GroqReply
from app.services.message_handler import (
    IncomingMessage,
    get_or_create_open_conversation,
    process_incoming_message,
    resolve_incoming_text,
)


@pytest.mark.asyncio
async def test_get_or_create_open_conversation_creates_new_when_none_exists(db_session):
    conversation = await get_or_create_open_conversation(db_session, "5598900000001")

    assert conversation.whatsapp_phone == "5598900000001"
    assert conversation.status == ConversationStatus.ABERTA


@pytest.mark.asyncio
async def test_get_or_create_open_conversation_reuses_open_conversation(db_session):
    existing = Conversation(whatsapp_phone="5598900000002")
    db_session.add(existing)
    await db_session.flush()

    found = await get_or_create_open_conversation(db_session, "5598900000002")

    assert found.id == existing.id


@pytest.mark.asyncio
async def test_get_or_create_open_conversation_ignores_resolved_conversations(db_session):
    resolved = Conversation(whatsapp_phone="5598900000003", status=ConversationStatus.RESOLVIDA)
    db_session.add(resolved)
    await db_session.flush()

    found = await get_or_create_open_conversation(db_session, "5598900000003")

    assert found.id != resolved.id


@pytest.mark.asyncio
async def test_resolve_incoming_text_returns_text_body_for_text_messages():
    content, tipo = await resolve_incoming_text(get_settings(), "text", "oi", None)
    assert (content, tipo) == ("oi", MessageType.TEXTO)


@pytest.mark.asyncio
async def test_resolve_incoming_text_defaults_to_empty_string_without_body():
    content, tipo = await resolve_incoming_text(get_settings(), "text", None, None)
    assert (content, tipo) == ("", MessageType.TEXTO)


@pytest.mark.asyncio
async def test_resolve_incoming_text_ignores_unsupported_message_types():
    content, tipo = await resolve_incoming_text(get_settings(), "sticker", None, None)
    assert (content, tipo) == ("", MessageType.TEXTO)


@pytest.mark.asyncio
async def test_resolve_incoming_text_transcribes_audio(monkeypatch):
    async def fake_get_media_url(settings, media_id):
        return "https://media.example/x"

    async def fake_download_media(settings, media_url, max_bytes):
        return b"raw-audio-bytes"

    seen_paths = []

    def fake_transcribe_audio(settings, path):
        seen_paths.append(path)
        return "transcrição falsa", "pt"

    monkeypatch.setattr(whatsapp_client, "get_media_url", fake_get_media_url)
    monkeypatch.setattr(whatsapp_client, "download_media", fake_download_media)
    monkeypatch.setattr(transcription_module, "transcribe_audio", fake_transcribe_audio)

    content, tipo = await resolve_incoming_text(get_settings(), "audio", None, "media-1")

    assert (content, tipo) == ("transcrição falsa", MessageType.AUDIO_TRANSCRITO)
    # LGPD: o áudio bruto nunca deve sobreviver à transcrição (só o texto é persistido).
    assert not Path(seen_paths[0]).exists()


@pytest.mark.asyncio
async def test_process_incoming_message_persists_reply_and_updates_status(
    db_session, sample_tours, monkeypatch
):
    db_session.add_all(sample_tours)
    await db_session.commit()

    sent = []

    async def fake_send_text_message(settings, to, body):
        sent.append(body)

    async def fake_ask_groq(settings, system_prompt, user_message):
        return GroqReply(idioma="es", precisa_atencao_humana=True, resposta="Ya llamo a alguien.")

    monkeypatch.setattr(whatsapp_client, "send_text_message", fake_send_text_message)
    monkeypatch.setattr(message_handler, "ask_groq", fake_ask_groq)

    conversation = await process_incoming_message(
        db_session, get_settings(), IncomingMessage("5598900000004", "text", "quiero un tour")
    )

    assert sent == ["Ya llamo a alguien."]
    assert conversation.idioma_detectado == "es"
    assert conversation.status == ConversationStatus.PRECISA_ATENCAO

    result = await db_session.execute(
        select(Message.conteudo)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    assert list(result.scalars().all()) == ["quiero un tour", "Ya llamo a alguien."]


@pytest.fixture
def oversized_audio(monkeypatch, pipeline_spies):
    """Simula um áudio acima do limite; devolve os espiões de envio, transcrição e Groq."""

    async def fake_get_media_url(settings, media_id):
        return "https://media.example/x"

    async def fake_download_media(settings, media_url, max_bytes):
        raise whatsapp_client.MediaTooLargeError(max_bytes)

    monkeypatch.setattr(whatsapp_client, "get_media_url", fake_get_media_url)
    monkeypatch.setattr(whatsapp_client, "download_media", fake_download_media)
    return pipeline_spies


@pytest.mark.asyncio
async def test_process_incoming_message_refuses_oversized_audio_without_transcribing(
    db_session, oversized_audio
):
    incoming = IncomingMessage("5598900000005", "audio", media_id="media-1")

    conversation = await process_incoming_message(db_session, get_settings(), incoming)

    assert oversized_audio["transcribed"] == []
    assert oversized_audio["asked"] == []
    assert oversized_audio["sent"] == [message_handler.AUDIO_TOO_LONG_REPLY]
    result = await db_session.execute(
        select(Message.tipo, Message.conteudo)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    # A entrada é TEXTO: o painel rotula AUDIO_TRANSCRITO como "transcrito de áudio".
    assert [tuple(row) for row in result] == [
        (MessageType.TEXTO, message_handler.AUDIO_TOO_LONG_NOTE),
        (MessageType.TEXTO, message_handler.AUDIO_TOO_LONG_REPLY),
    ]


@pytest.mark.asyncio
async def test_resolve_incoming_text_passes_configured_limit_to_download(monkeypatch):
    seen = []

    async def fake_get_media_url(settings, media_id):
        return "https://media.example/x"

    async def fake_download_media(settings, media_url, max_bytes):
        seen.append(max_bytes)
        return b"audio"

    monkeypatch.setattr(whatsapp_client, "get_media_url", fake_get_media_url)
    monkeypatch.setattr(whatsapp_client, "download_media", fake_download_media)
    monkeypatch.setattr(transcription_module, "transcribe_audio", lambda s, p: ("ok", "pt"))
    settings = get_settings()
    monkeypatch.setattr(settings, "max_audio_bytes", 1234)

    await resolve_incoming_text(settings, "audio", None, "media-1")

    assert seen == [1234]


@pytest.mark.asyncio
async def test_process_incoming_message_logs_oversized_audio_without_personal_data(
    db_session, oversized_audio, caplog
):
    incoming = IncomingMessage("5598900000006", "audio", media_id="media-1")

    with caplog.at_level("INFO", logger=message_handler.logger.name):
        await process_incoming_message(db_session, get_settings(), incoming)

    assert "áudio recusado" in caplog.text
    assert "5598900000006" not in caplog.text
