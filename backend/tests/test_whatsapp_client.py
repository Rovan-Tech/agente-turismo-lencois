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

    audio_bytes = await whatsapp_client.download_media(settings, "https://media.example/x", 1024)

    assert audio_bytes == b"audio-bytes"


@pytest.mark.asyncio
async def test_download_media_accepts_body_exactly_at_the_limit(settings, monkeypatch):
    _install_mock_transport(monkeypatch, lambda request: httpx.Response(200, content=b"12345"))

    audio_bytes = await whatsapp_client.download_media(settings, "https://media.example/x", 5)

    assert audio_bytes == b"12345"


async def _chunks(reads):
    for _ in range(100):
        reads.append(1)
        yield b"x" * 4


def _declared_oversized(reads):
    return lambda request: httpx.Response(200, headers={"Content-Length": "999999"}, content=b"x")


def _streamed_oversized(reads):
    return lambda request: httpx.Response(200, content=_chunks(reads))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_handler",
    [_declared_oversized, _streamed_oversized],
    ids=["content-length-declared", "streamed-without-content-length"],
)
async def test_download_media_rejects_body_over_limit_and_stops_reading(
    settings, monkeypatch, make_handler
):
    reads: list[int] = []
    _install_mock_transport(monkeypatch, make_handler(reads))

    with pytest.raises(whatsapp_client.MediaTooLargeError):
        await whatsapp_client.download_media(settings, "https://media.example/x", 10)
    assert len(reads) < 100


@pytest.mark.asyncio
async def test_download_media_asks_for_uncompressed_body(settings, monkeypatch):
    seen = []

    def handler(request):
        seen.append(request.headers.get("Accept-Encoding"))
        return httpx.Response(200, content=b"ok")

    _install_mock_transport(monkeypatch, handler)

    await whatsapp_client.download_media(settings, "https://media.example/x", 10)

    assert seen == ["identity"]
