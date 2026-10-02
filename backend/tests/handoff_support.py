"""Apoio dos testes do atendimento humano: conversas prontas e um WhatsApp de mentira."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageAuthor, MessageDirection
from tests.access_support import AccessEnv, panel_headers

PHONE = "5598912171865"


@dataclass
class Outbox:
    """O que o backend mandou ao WhatsApp; `failure` faz o próximo envio falhar."""

    sent: list[tuple[str, str]] = field(default_factory=list)
    failure: Exception | None = None


def meta_rejection(code: int = 131047) -> httpx.HTTPStatusError:
    """Recusa da Meta como o `httpx` a levanta, com URL (leva o phone_number_id) e corpo do erro."""
    request = httpx.Request("POST", "https://graph.facebook.com/v21.0/PHONE_ID_SECRETO/messages")
    response = httpx.Response(
        400, json={"error": {"code": code, "message": "detalhe-interno-da-meta"}}, request=request
    )
    # A mensagem real do httpx traz a URL, e com ela o phone_number_id: o log não pode repeti-la.
    message = f"Client error '400 Bad Request' for url '{request.url}'"
    return httpx.HTTPStatusError(message, request=request, response=response)


def meta_html_error() -> httpx.HTTPStatusError:
    """Recusa sem JSON (como a de um proxy fora do ar): não há código da Meta para mostrar."""
    request = httpx.Request("POST", "https://graph.facebook.com/v21.0/PHONE_ID_SECRETO/messages")
    response = httpx.Response(502, text="<html>bad gateway</html>", request=request)
    return httpx.HTTPStatusError("Bad gateway", request=request, response=response)


async def make_conversation(
    db: AsyncSession,
    *,
    phone: str = PHONE,
    language: str | None = "pt",
    tourist_minutes_ago: int | None = 5,
    status: ConversationStatus = ConversationStatus.ABERTA,
    **fields: object,
) -> Conversation:
    """Conversa com uma mensagem do turista `tourist_minutes_ago` minutos atrás (None = nenhuma)."""
    conversation = Conversation(
        whatsapp_phone=phone, idioma_detectado=language, status=status, **fields
    )
    db.add(conversation)
    await db.flush()
    if tourist_minutes_ago is not None:
        db.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.ENTRADA,
                autor=MessageAuthor.TURISTA,
                conteudo="quero ver o passeio",
                created_at=datetime.now(UTC) - timedelta(minutes=tourist_minutes_ago),
            )
        )
    await db.commit()
    return conversation


async def all_messages(db: AsyncSession) -> list[Message]:
    """Todas as mensagens gravadas, da mais antiga para a mais nova."""
    result = await db.execute(select(Message).order_by(Message.created_at, Message.id))
    return list(result.scalars().all())


async def act(
    client: httpx.AsyncClient,
    conversation: Conversation,
    action: str,
    headers: dict[str, str],
    body: dict[str, object] | None = None,
) -> httpx.Response:
    """POST em `/api/conversations/{id}/{action}` com os cabeçalhos dados."""
    return await client.post(
        f"/api/conversations/{conversation.id}/{action}", json=body, headers=headers
    )


async def take_over(
    client: httpx.AsyncClient, access: AccessEnv, conversation: Conversation, token: str = ""
) -> httpx.Response:
    """A pessoa logada (ou a do `token` dado) assume a conversa."""
    return await act(client, conversation, "assumir", panel_headers(token or access.token()))


async def give_back(
    client: httpx.AsyncClient, access: AccessEnv, conversation: Conversation
) -> httpx.Response:
    """A pessoa logada devolve a conversa para a IA."""
    return await act(client, conversation, "devolver", panel_headers(access.token()))


def assert_refused(response: httpx.Response, outbox: Outbox, status: int = 409) -> None:
    """O pedido foi recusado com `status` e nada foi enviado ao WhatsApp."""
    assert response.status_code == status
    assert outbox.sent == []


async def holding(
    db: AsyncSession,
    *,
    hours_ago: float = 0.1,
    phone: str = PHONE,
    tourist_minutes_ago: int | None = 5,
    status: ConversationStatus = ConversationStatus.ABERTA,
) -> Conversation:
    """Conversa já com a pessoa `pessoa-123`, cuja última atividade foi há `hours_ago` horas."""
    moment = datetime.now(UTC) - timedelta(hours=hours_ago)
    return await make_conversation(
        db,
        phone=phone,
        tourist_minutes_ago=tourist_minutes_ago,
        status=status,
        atendimento="humano",
        humano_sub="pessoa-123",
        humano_nome="Pessoa",
        humano_desde=moment,
        humano_atividade_em=moment,
    )
