from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.models.conversation import Conversation

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(require_dashboard_auth)],
)


@router.get("")
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    conversations = result.scalars().all()
    return [
        {
            "id": c.id,
            "whatsapp_phone": c.whatsapp_phone,
            "status": c.status,
            "idioma_detectado": c.idioma_detectado,
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="conversa não encontrada")

    return {
        "id": conversation.id,
        "whatsapp_phone": conversation.whatsapp_phone,
        "status": conversation.status,
        "idioma_detectado": conversation.idioma_detectado,
        "messages": [
            {
                "id": m.id,
                "direction": m.direction,
                "tipo": m.tipo,
                "conteudo": m.conteudo,
                "idioma": m.idioma,
                "created_at": m.created_at.isoformat(),
            }
            for m in conversation.messages
        ],
    }
