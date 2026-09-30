import httpx
import pytest

from app.core.config import get_settings
from app.services import whatsapp_client


@pytest.fixture
def settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_api_base_url", "https://graph.example")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "1234567890")
    monkeypatch.setattr(settings, "whatsapp_token", "fake-value")
    return settings


def _install_mock_transport(monkeypatch, handler):
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_send_text_message_posts_expected_payload_and_headers(settings, monkeypatch):
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    _install_mock_transport(monkeypatch, handler)

    await whatsapp_client.send_text_message(settings, "5598999998888", "Olá!")

    body = captured["body"]
    assert isinstance(body, bytes)
    assert captured["url"] == "https://graph.example/1234567890/messages"
    assert captured["authorization"] == "Bearer fake-value"
    assert b'"to":"5598999998888"' in body


@pytest.mark.asyncio
async def test_send_text_message_raises_for_http_error_status(settings, monkeypatch):
    _install_mock_transport(monkeypatch, lambda request: httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        await whatsapp_client.send_text_message(settings, "5598999998888", "Olá!")


@pytest.mark.asyncio
async def test_get_media_url_returns_url_from_response(settings, monkeypatch):
    _install_mock_transport(
        monkeypatch, lambda request: httpx.Response(200, json={"url": "https://media.example/x"})
    )

    media_url = await whatsapp_client.get_media_url(settings, "media-1")

    assert media_url == "https://media.example/x"


@pytest.mark.asyncio
async def test_download_media_returns_bytes(settings, monkeypatch):
    _install_mock_transport(
        monkeypatch, lambda request: httpx.Response(200, content=b"audio-bytes")
    )

    audio_bytes = await whatsapp_client.download_media(settings, "https://media.example/x")

    assert audio_bytes == b"audio-bytes"
