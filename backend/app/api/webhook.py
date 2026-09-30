from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import is_valid_whatsapp_signature
from app.db.session import get_db
from app.services.message_handler import IncomingMessage, process_incoming_message

router = APIRouter(prefix="/webhook/whatsapp", tags=["webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> Response:
    if hub_mode != "subscribe" or hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="verificação inválida")
    return Response(content=hub_challenge, media_type="text/plain")


def _extract_messages(payload: dict) -> list[dict]:
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))
    return messages


@router.post("")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict:
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

    for msg in _extract_messages(payload):
        phone = msg.get("from")
        msg_type = msg.get("type")
        if not phone or not msg_type:
            continue

        if msg_type == "text":
            text_body = msg.get("text", {}).get("body")
            await process_incoming_message(db, settings, IncomingMessage(phone, "text", text_body))
        elif msg_type == "audio":
            media_id = msg.get("audio", {}).get("id")
            await process_incoming_message(
                db, settings, IncomingMessage(phone, "audio", media_id=media_id)
            )

    return {"status": "ok"}
