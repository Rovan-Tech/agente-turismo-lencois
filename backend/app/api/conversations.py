from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import Select, Subquery, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_dashboard_auth, require_panel_identity
from app.api.errors import CONFLICT, CONVERSATION_NOT_FOUND, NOT_FOUND
from app.core.access_jwt import AccessIdentity
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.conversation import Conversation, ConversationStatus, Handling
from app.models.message import Message
from app.services import handoff

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


class EmptyBody(BaseModel):
    """Corpo de assumir e devolver: sem campos, para o nome e o telefone nunca virem do cliente."""

    model_config = ConfigDict(strict=True, extra="forbid")


class ReplyBody(BaseModel):
    """Resposta do atendente: só o texto e o id do envio; o destinatário é o da conversa."""

    model_config = ConfigDict(strict=True, extra="forbid")

    # 1 a 4096 (o teto do WhatsApp), sem NUL (o Postgres o recusa).
    texto: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=4096, pattern=r"^[^\x00]*$"
        ),
    ]
    client_message_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")


@contextmanager
def _handoff_errors() -> Iterator[None]:
    """Traduz a recusa de uma regra do atendimento no erro HTTP correspondente."""
    try:
        yield
    except handoff.HandoffError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None


def locked_conversation_query(conversation_id: str) -> Select[tuple[Conversation]]:
    """Consulta que trava a linha até o fim da transação (`FOR UPDATE`; sem efeito no SQLite).

    Assumir, devolver e enviar leem o estado e depois o mudam: sem a trava, dois cliques ou duas
    pessoas ao mesmo tempo passariam juntos pela checagem e o turista receberia dois avisos.
    `populate_existing` relê a linha depois da espera, em vez de usar o objeto já em memória.
    """
    return (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def _load(db: AsyncSession, conversation_id: str, *, lock: bool = False) -> Conversation:
    if lock:
        conversation = (
            await db.execute(locked_conversation_query(conversation_id))
        ).scalar_one_or_none()
    else:
        conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail=CONVERSATION_NOT_FOUND)
    return conversation


def _message_dict(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "direction": message.direction,
        "tipo": message.tipo,
        "conteudo": message.conteudo,
        "idioma": message.idioma,
        "autor": message.autor,
        "created_at": _iso(message.created_at),
    }


def _iso(moment: datetime) -> str:
    """ISO 8601 sempre com fuso: o SQLite devolve datas sem ele e o navegador leria como local."""
    return (moment if moment.tzinfo else moment.replace(tzinfo=UTC)).isoformat()


def _summary(conversation: Conversation, settings: Settings) -> dict[str, object]:
    is_human = handoff.current_handling(conversation, settings) == Handling.HUMANO
    return {
        "id": conversation.id,
        "whatsapp_phone": conversation.whatsapp_phone,
        "status": conversation.status,
        "idioma_detectado": conversation.idioma_detectado,
        "atendimento": Handling.HUMANO if is_human else Handling.IA,
        "atendente_nome": conversation.humano_nome if is_human else None,
        "atendente_sub": conversation.humano_sub if is_human else None,
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
async def list_conversations(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> list[dict[str, object]]:
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
            **_summary(conversation, settings),
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


@router.patch("/{conversation_id}/status", responses={404: NOT_FOUND})
async def update_conversation_status(
    conversation_id: str,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Troca o status da conversa. Resolver também devolve a conversa para a IA."""
    # Travada: resolver em paralelo com assumir deixaria a conversa resolvida e ainda `humano`.
    conversation = await _load(db, conversation_id, lock=True)
    conversation.status = payload.status
    if payload.status == ConversationStatus.RESOLVIDA:
        handoff.clear_handling(conversation)
    await db.commit()
    return _summary(conversation, settings)


Action = Callable[[AsyncSession, Settings, Conversation, AccessIdentity], Awaitable[Conversation]]


@dataclass(frozen=True, slots=True)
class PanelContext:
    """O que toda ação de atendimento precisa: banco, configuração e quem está logado."""

    db: AsyncSession
    settings: Settings
    identity: AccessIdentity


def panel_context(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    identity: AccessIdentity = Depends(require_panel_identity),
) -> PanelContext:
    """Junta banco, configuração e a pessoa logada (exige login por pessoa, não o token fixo)."""
    return PanelContext(db, settings, identity)


async def _run_action(action: Action, conversation_id: str, ctx: PanelContext) -> dict[str, object]:
    conversation = await _load(ctx.db, conversation_id, lock=True)
    with _handoff_errors():
        await action(ctx.db, ctx.settings, conversation, ctx.identity)
    return _summary(conversation, ctx.settings)


@router.post("/{conversation_id}/assumir", responses={404: NOT_FOUND, 409: CONFLICT})
async def take_over_conversation(
    conversation_id: str, ctx: PanelContext = Depends(panel_context), _body: EmptyBody | None = None
) -> dict[str, object]:
    """A pessoa logada assume a conversa; o turista recebe o aviso com o primeiro nome dela.

    409 se a conversa já está com outra pessoa ("A conversa já está com <nome>. Peça para devolver
    à IA."): a conversa continua com quem a assumiu primeiro e nada é enviado ao turista. Também
    é 409 quando está resolvida ou a janela de 24 h do WhatsApp fechou.
    """
    return await _run_action(handoff.take_over, conversation_id, ctx)


@router.post("/{conversation_id}/devolver", responses={404: NOT_FOUND})
async def give_back_conversation(
    conversation_id: str, ctx: PanelContext = Depends(panel_context), _body: EmptyBody | None = None
) -> dict[str, object]:
    """Devolve a conversa para a IA (qualquer pessoa logada pode, para liberar uma esquecida)."""
    return await _run_action(handoff.give_back, conversation_id, ctx)


@router.post("/{conversation_id}/mensagens", responses={404: NOT_FOUND, 409: CONFLICT})
async def send_conversation_message(
    conversation_id: str, payload: ReplyBody, ctx: PanelContext = Depends(panel_context)
) -> dict[str, object]:
    """Envia a resposta do atendente ao WhatsApp do turista desta conversa e a grava."""
    conversation = await _load(ctx.db, conversation_id, lock=True)
    outgoing = handoff.OutgoingText(payload.texto, payload.client_message_id)
    with _handoff_errors():
        message = await handoff.send_message(
            ctx.db, ctx.settings, conversation, ctx.identity, outgoing
        )
    return _message_dict(message)


@router.get("/{conversation_id}", responses={404: NOT_FOUND})
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Devolve a conversa com todas as mensagens, ou 404 se não existir."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.passeio_sugerido))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail=CONVERSATION_NOT_FOUND)

    suggested = conversation.passeio_sugerido
    return {
        **_summary(conversation, settings),
        "passeio_sugerido": suggested.to_catalog_dict() if suggested else None,
        "messages": [_message_dict(m) for m in conversation.messages],
    }
