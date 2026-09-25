from __future__ import annotations

import tempfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.models.tour import Tour
from app.services import tour_matcher, whatsapp_client
from app.services.groq_client import ask_groq, build_system_prompt


async def get_or_create_open_conversation(db: AsyncSession, phone: str) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_phone == phone)
        .where(Conversation.status != ConversationStatus.RESOLVIDA)
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalars().first()
    if conversation:
        return conversation

    conversation = Conversation(whatsapp_phone=phone)
    db.add(conversation)
    await db.flush()
    return conversation


async def resolve_incoming_text(
    settings: Settings, message_type: str, text_body: str | None, media_id: str | None
) -> tuple[str, MessageType]:
    if message_type == "text":
        return text_body or "", MessageType.TEXTO

    if message_type == "audio" and media_id:
        media_url = await whatsapp_client.get_media_url(settings, media_id)
        audio_bytes = await whatsapp_client.download_media(settings, media_url)

        from app.services.transcription import transcribe_audio

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            text, _language = transcribe_audio(settings, tmp_file.name)
        return text, MessageType.AUDIO_TRANSCRITO

    return "", MessageType.TEXTO


async def process_incoming_message(
    db: AsyncSession,
    settings: Settings,
    phone: str,
    message_type: str,
    text_body: str | None = None,
    media_id: str | None = None,
) -> Conversation:
    conversation = await get_or_create_open_conversation(db, phone)

    content, tipo = await resolve_incoming_text(settings, message_type, text_body, media_id)

    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.ENTRADA,
            tipo=tipo,
            conteudo=content,
        )
    )

    result = await db.execute(select(Tour).where(Tour.ativo.is_(True)))
    active_tours = list(result.scalars().all())
    candidate_tours = tour_matcher.select_candidate_tours(active_tours, content)

    system_prompt = build_system_prompt(settings.agency_name, candidate_tours)
    reply = await ask_groq(settings, system_prompt, content)

    db.add(
        Message(
            conversation_id=conversation.id,
            direction=MessageDirection.SAIDA,
            tipo=MessageType.TEXTO,
            conteudo=reply.resposta,
            idioma=reply.idioma,
        )
    )

    conversation.idioma_detectado = reply.idioma
    conversation.status = (
        ConversationStatus.PRECISA_ATENCAO
        if reply.precisa_atencao_humana
        else ConversationStatus.ABERTA
    )

    await db.commit()

    await whatsapp_client.send_text_message(settings, phone, reply.resposta)

    return conversation
