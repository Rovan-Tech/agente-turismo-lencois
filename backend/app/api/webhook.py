from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import BAD_REQUEST, FORBIDDEN
from app.core.config import Settings, get_settings
from app.core.security import is_valid_whatsapp_signature
from app.db.session import get_db
from app.services.customer_name import clean_profile_name
from app.services.message_handler import IncomingMessage, process_incoming_message

router = APIRouter(prefix="/webhook/whatsapp", tags=["webhook"])


@router.get("", responses={403: FORBIDDEN})
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> Response:
    if hub_mode != "subscribe" or hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="verificação inválida")
    return Response(content=hub_challenge, media_type="text/plain")


def _profile_names(value: dict[str, Any]) -> dict[str, object]:
    """Nome do perfil por `wa_id`, de `contacts[].profile.name` (a Meta o manda com as mensagens).

    O payload é dado não confiável: contato ou perfil que não sejam objetos são ignorados.
    """
    names: dict[str, object] = {}
    for contact in value.get("contacts", []):
        if not isinstance(contact, dict) or not isinstance(contact.get("wa_id"), str):
            continue
        profile = contact.get("profile")
        names[contact["wa_id"]] = profile.get("name") if isinstance(profile, dict) else None
    return names


def _extract_messages(payload: dict[str, Any]) -> list[tuple[dict[str, Any], object]]:
    """Mensagens do payload, cada uma com o nome do perfil de quem a enviou (ou `None`)."""
    messages: list[tuple[dict[str, Any], object]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = _profile_names(value)
            for msg in value.get("messages", []):
                sender = msg.get("from")
                messages.append((msg, names.get(sender) if isinstance(sender, str) else None))
    return messages


MAX_MESSAGE_ID_LENGTH = 128  # tamanho da coluna `messages.whatsapp_message_id`


def _valid_message_id(value: object) -> str | None:
    """Aceita só um id de texto não vazio que caiba na coluna; o resto vira "sem id"."""
    if isinstance(value, str) and 0 < len(value) <= MAX_MESSAGE_ID_LENGTH:
        return value
    return None


def _to_incoming(msg: dict[str, Any], profile_name: object) -> IncomingMessage | None:
    """Converte uma mensagem do payload da Meta; `None` para tipos que o bot não atende."""
    phone = msg.get("from")
    msg_type = msg.get("type")
    if not phone or msg_type not in ("text", "audio"):
        return None
    message_id = _valid_message_id(msg.get("id"))
    name = clean_profile_name(profile_name)
    if msg_type == "text":
        return IncomingMessage(
            phone, "text", msg.get("text", {}).get("body"), message_id=message_id, profile_name=name
        )
    return IncomingMessage(
        phone,
        "audio",
        media_id=msg.get("audio", {}).get("id"),
        message_id=message_id,
        profile_name=name,
    )


@router.post("", responses={400: BAD_REQUEST, 403: FORBIDDEN})
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    raw_body = await request.body()

    if settings.whatsapp_app_secret and not is_valid_whatsapp_signature(
        raw_body, x_hub_signature_256, settings.whatsapp_app_secret
    ):
        raise HTTPException(status_code=403, detail="assinatura inválida")

    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="payload inválido") from None

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload inválido")

    # Processa na própria requisição: no Cloud Run o trabalho depois da resposta não tem CPU
    # garantida. Se a Meta reenviar por demora, o `message_id` faz o reenvio ser descartado.
    for msg, profile_name in _extract_messages(payload):
        incoming = _to_incoming(msg, profile_name)
        if incoming:
            await process_incoming_message(db, settings, incoming)

    return {"status": "ok"}
