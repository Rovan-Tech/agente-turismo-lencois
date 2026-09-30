from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.models.conversation import Conversation, ConversationStatus

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(require_dashboard_auth)],
)


class StatusUpdate(BaseModel):
    """Única mudança manual de status permitida: `aberta`/`precisa_atencao` continuam da IA."""

    status: Literal["resolvida"]


def _summary(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "whatsapp_phone": conversation.whatsapp_phone,
        "status": conversation.status,
        "idioma_detectado": conversation.idioma_detectado,
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.get("")
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    """Lista as conversas: pendentes primeiro (mais recentes antes), resolvidas por último."""
    # Resolvidas por último: marcar como resolvida atualiza `updated_at`, e uma conversa já
    # atendida não deve subir ao topo da fila.
    resolved_last = case((Conversation.status == ConversationStatus.RESOLVIDA, 1), else_=0)
    result = await db.execute(
        select(Conversation).order_by(resolved_last, Conversation.updated_at.desc())
    )
    return [_summary(c) for c in result.scalars().all()]


@router.patch("/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: str, payload: StatusUpdate, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Marca a conversa como resolvida; qualquer outro status é recusado (422) pelo schema."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversa não encontrada")

    conversation.status = ConversationStatus(payload.status)
    await db.commit()
    return _summary(conversation)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Devolve a conversa com todas as mensagens, ou 404 se não existir."""
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
