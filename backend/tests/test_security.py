import hashlib
import hmac

import pytest

from app.core.security import is_valid_dashboard_token, is_valid_whatsapp_signature


def _sign(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted():
    payload = b'{"entry": []}'
    secret = "s3cret"
    assert is_valid_whatsapp_signature(payload, _sign(payload, secret), secret) is True


def test_tampered_payload_is_rejected():
    payload = b'{"entry": []}'
    secret = "s3cret"
    signature = _sign(payload, secret)
    assert is_valid_whatsapp_signature(b'{"entry": ["tampered"]}', signature, secret) is False


def test_missing_signature_header_is_rejected():
    assert is_valid_whatsapp_signature(b"{}", None, "s3cret") is False


def test_signature_without_prefix_is_rejected():
    assert is_valid_whatsapp_signature(b"{}", "deadbeef", "s3cret") is False


def test_empty_app_secret_is_rejected():
    assert is_valid_whatsapp_signature(b"{}", "sha256=deadbeef", "") is False


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "s3cret")
    response = await client.post(
        "/webhook/whatsapp",
        json={"entry": []},
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_rejects_malformed_json(client):
    response = await client.post(
        "/webhook/whatsapp",
        content=b"isto nao e json valido {",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_rejects_non_object_payload(client):
    response = await client.post("/webhook/whatsapp", json=["array", "não", "objeto"])
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_verification_rejects_wrong_token(client):
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-errado",
            "hub.challenge": "123",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_verification_accepts_correct_token(client):
    from app.core.config import get_settings

    settings = get_settings()
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.whatsapp_verify_token,
            "hub.challenge": "123",
        },
    )
    assert response.status_code == 200
    assert response.text == "123"


@pytest.mark.asyncio
async def test_webhook_ignores_unexpected_method(client):
    response = await client.put("/webhook/whatsapp", json={})
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_cors_blocks_untrusted_origin(client):
    response = await client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_valid_dashboard_token_is_accepted():
    assert is_valid_dashboard_token("Bearer abc123", "abc123") is True


def test_wrong_dashboard_token_is_rejected():
    assert is_valid_dashboard_token("Bearer wrong", "abc123") is False


def test_missing_authorization_header_is_rejected():
    assert is_valid_dashboard_token(None, "abc123") is False


def test_authorization_header_without_bearer_prefix_is_rejected():
    assert is_valid_dashboard_token("abc123", "abc123") is False


def test_empty_expected_token_always_rejects():
    assert is_valid_dashboard_token("Bearer anything", "") is False


@pytest.mark.asyncio
async def test_tours_endpoint_requires_dashboard_token(client):
    response = await client.get("/api/tours", headers={"Authorization": ""})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_conversations_endpoint_rejects_wrong_token(client):
    response = await client.get(
        "/api/conversations", headers={"Authorization": "Bearer token-errado"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_conversations_endpoint_accepts_valid_token(client):
    response = await client.get("/api/conversations")
    assert response.status_code == 200
