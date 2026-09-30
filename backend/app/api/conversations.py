from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Subquery, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_dashboard_auth
from app.db.session import get_db
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message

# A lista só mostra uma prévia da última mensagem: limitar o tamanho mantém a resposta leve.
PREVIEW_LENGTH = 200

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    dependencies=[Depends(require_dashboard_auth)],
)


class StatusUpdate(BaseModel):
    """Novo status escolhido pela equipe no painel (qualquer um dos três, inclusive reabrir)."""

    status: ConversationStatus


def _iso(moment: datetime) -> str:
    """ISO 8601 sempre com fuso: o SQLite devolve datas sem ele e o navegador leria como local."""
    return (moment if moment.tzinfo else moment.replace(tzinfo=UTC)).isoformat()


def _summary(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "whatsapp_phone": conversation.whatsapp_phone,
        "status": conversation.status,
        "idioma_detectado": conversation.idioma_detectado,
        "created_at": _iso(conversation.created_at),
        "updated_at": _iso(conversation.updated_at),
    }


def _last_message_subquery() -> Subquery:
    """Uma linha por conversa: a mensagem mais recente (prévia truncada)."""
    ranked = select(
        Message.conversation_id,
        func.substr(Message.conteudo, 1, PREVIEW_LENGTH).label("conteudo"),
        Message.tipo,
        Message.direction,
        Message.created_at.label("sent_at"),
        func.row_number()
        .over(
            partition_by=Message.conversation_id,
            order_by=(Message.created_at.desc(), Message.id.desc()),
        )
        .label("position"),
    ).subquery()
    return select(ranked).where(ranked.c.position == 1).subquery()


@router.get("")
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    """Lista as conversas: pendentes primeiro (mais recentes antes), resolvidas por último."""
    # Resolvidas por último: marcar como resolvida atualiza `updated_at`, e uma conversa já
    # atendida não deve subir ao topo da fila.
    resolved_last = case((Conversation.status == ConversationStatus.RESOLVIDA, 1), else_=0)
    last = _last_message_subquery()
    result = await db.execute(
        select(Conversation, last.c.conteudo, last.c.tipo, last.c.direction, last.c.sent_at)
        .outerjoin(last, last.c.conversation_id == Conversation.id)
        .order_by(resolved_last, Conversation.updated_at.desc())
    )
    return [
        {
            **_summary(conversation),
            "ultima_mensagem": (
                None
                if conteudo is None
                else {
                    "conteudo": conteudo,
                    "tipo": tipo,
                    "direction": direction,
                    "created_at": _iso(sent_at),
                }
            ),
        }
        for conversation, conteudo, tipo, direction, sent_at in result.all()
    ]


@router.patch("/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: str, payload: StatusUpdate, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Troca o status da conversa. O assistente ainda o reavalia a cada nova mensagem do turista."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversa não encontrada")

    conversation.status = payload.status
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
        **_summary(conversation),
        "messages": [
            {
                "id": m.id,
                "direction": m.direction,
                "tipo": m.tipo,
                "conteudo": m.conteudo,
                "idioma": m.idioma,
                "created_at": _iso(m.created_at),
            }
            for m in conversation.messages
        ],
    }
