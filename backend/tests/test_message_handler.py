from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
from tests.handoff_support import PHONE, holding


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

    assert conversation is not None
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

    assert conversation is not None
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


async def _process(db, incoming):
    return await process_incoming_message(db, get_settings(), incoming)


@pytest.mark.asyncio
async def test_process_incoming_message_skips_message_id_already_stored(db_session, pipeline_spies):
    incoming = IncomingMessage("5598900000010", "text", "oi", message_id="wamid.x")

    first = await _process(db_session, incoming)
    second = await _process(db_session, incoming)

    assert (first is None, second is None) == (False, True)
    assert pipeline_spies["asked"] == ["oi"]
    assert pipeline_spies["sent"] == ["ok"]


@pytest.mark.asyncio
async def test_process_incoming_message_drops_concurrent_duplicate_on_unique_conflict(
    db_session, pipeline_spies, blind_duplicate_check
):
    """Dois reenvios em paralelo: o segundo passa da checagem, mas o índice único o barra."""
    incoming = IncomingMessage("5598900000011", "text", "oi", message_id="wamid.corrida")
    await _process(db_session, incoming)

    assert await _process(db_session, incoming) is None
    assert pipeline_spies["asked"] == ["oi"]
    assert pipeline_spies["sent"] == ["ok"]


@pytest.mark.asyncio
async def test_process_incoming_message_without_message_id_is_never_a_duplicate(
    db_session, pipeline_spies
):
    incoming = IncomingMessage("5598900000012", "text", "oi")

    await _process(db_session, incoming)
    await _process(db_session, incoming)

    assert pipeline_spies["asked"] == ["oi", "oi"]


@pytest.mark.asyncio
async def test_duplicate_audio_is_skipped_before_downloading(
    db_session, oversized_audio, monkeypatch
):
    downloads: list[str] = []

    async def counting_download(settings, media_url, max_bytes):
        downloads.append(media_url)
        raise whatsapp_client.MediaTooLargeError(max_bytes)

    monkeypatch.setattr(whatsapp_client, "download_media", counting_download)
    incoming = IncomingMessage("5598900000013", "audio", media_id="m1", message_id="wamid.audio")

    await _process(db_session, incoming)
    await _process(db_session, incoming)

    assert len(downloads) == 1
    assert oversized_audio["sent"] == [message_handler.AUDIO_TOO_LONG_REPLY]


class _WhatsAppDownError(Exception):
    pass


@pytest.mark.asyncio
async def test_failed_send_leaves_message_unrecorded_so_the_retry_is_processed(
    db_session, pipeline_spies, monkeypatch
):
    incoming = IncomingMessage("5598900000014", "text", "oi", message_id="wamid.envio")
    working_send = whatsapp_client.send_text_message

    async def failing_send(settings, to, body):
        raise _WhatsAppDownError

    monkeypatch.setattr(whatsapp_client, "send_text_message", failing_send)
    with pytest.raises(_WhatsAppDownError):
        await _process(db_session, incoming)
    await db_session.rollback()  # o fim da requisição descarta a transação, como em produção

    monkeypatch.setattr(whatsapp_client, "send_text_message", working_send)
    retried = await _process(db_session, incoming)

    assert retried is not None
    assert pipeline_spies["sent"] == ["ok"]
    stored = await db_session.execute(select(Message.conteudo).order_by(Message.created_at))
    assert list(stored.scalars().all()) == ["oi", "ok"]


@pytest.mark.asyncio
async def test_concurrent_duplicate_oversized_audio_is_dropped_without_a_second_reply(
    db_session, oversized_audio, blind_duplicate_check
):
    incoming = IncomingMessage("5598900000015", "audio", media_id="m2", message_id="wamid.audio2")
    await _process(db_session, incoming)

    assert await _process(db_session, incoming) is None
    assert oversized_audio["sent"] == [message_handler.AUDIO_TOO_LONG_REPLY]


@pytest.mark.asyncio
async def test_integrity_error_without_message_id_is_not_mistaken_for_a_duplicate(
    db_session, monkeypatch
):
    conversation = await get_or_create_open_conversation(db_session, "5598900000016")
    incoming = IncomingMessage("5598900000016", "text", "oi")

    async def failing_flush():
        raise IntegrityError("INSERT", {}, ValueError("outra constraint"))

    monkeypatch.setattr(db_session, "flush", failing_flush)

    with pytest.raises(IntegrityError):
        await message_handler.store_incoming(
            db_session, conversation, incoming, MessageType.TEXTO, "oi"
        )


@pytest.mark.asyncio
async def test_process_incoming_message_oversized_audio_with_an_attendant_is_noted_without_a_reply(
    db_session, oversized_audio
):
    await holding(db_session)
    incoming = IncomingMessage(PHONE, "audio", media_id="m1", message_id="wamid.audio-humano")

    await _process(db_session, incoming)

    notes = await db_session.execute(
        select(Message.conteudo).where(Message.conteudo == message_handler.AUDIO_TOO_LONG_NOTE)
    )
    assert oversized_audio["sent"] == []
    assert len(notes.all()) == 1
