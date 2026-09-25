from __future__ import annotations

import httpx

from app.core.config import Settings


async def send_text_message(settings: Settings, to: str, body: str) -> None:
    url = f"{settings.whatsapp_api_base_url}/{settings.whatsapp_phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()


async def get_media_url(settings: Settings, media_id: str) -> str:
    url = f"{settings.whatsapp_api_base_url}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["url"]


async def download_media(settings: Settings, media_url: str) -> bytes:
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(media_url, headers=headers)
        response.raise_for_status()
        return response.content
