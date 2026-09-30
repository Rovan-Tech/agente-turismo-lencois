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


class MediaTooLargeError(Exception):
    """A mídia recebida da Meta passa do tamanho máximo aceito."""

    def __init__(self, max_bytes: int) -> None:
        """Guarda o teto que foi excedido."""
        super().__init__(f"mídia acima do limite de {max_bytes} bytes")
        self.max_bytes = max_bytes


async def download_media(settings: Settings, media_url: str, max_bytes: int) -> bytes:
    """Baixa a mídia em streaming e aborta assim que passar de `max_bytes`.

    Args:
        settings: Configurações com o token da API do WhatsApp.
        media_url: URL de download da mídia informada pela Meta.
        max_bytes: Tamanho máximo aceito, em bytes.

    Returns:
        Os bytes da mídia baixada.

    Raises:
        MediaTooLargeError: `Content-Length` declarado ou corpo recebido acima do limite.
    """
    # `identity`: áudio Opus não comprime, e assim o teto vale para os bytes que chegam de fato.
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}", "Accept-Encoding": "identity"}
    async with (
        httpx.AsyncClient(timeout=30) as client,
        client.stream("GET", media_url, headers=headers) as response,
    ):
        response.raise_for_status()
        declared = response.headers.get("Content-Length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            raise MediaTooLargeError(max_bytes)
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise MediaTooLargeError(max_bytes)
        return bytes(body)
