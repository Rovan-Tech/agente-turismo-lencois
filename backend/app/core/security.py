import hashlib
import hmac


def is_valid_whatsapp_signature(
    payload: bytes, signature_header: str | None, app_secret: str
) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    if not app_secret:
        return False
    expected = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def is_valid_bearer_token(authorization_header: str | None, expected_token: str) -> bool:
    """Confere `Authorization: Bearer <token>` em tempo constante; sem token esperado, nega."""
    if not expected_token:
        return False
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    received = authorization_header.removeprefix("Bearer ")
    # Em bytes: `compare_digest` com `str` levanta TypeError se o cabeçalho tiver não-ASCII.
    return hmac.compare_digest(received.encode(), expected_token.encode())


def is_valid_dashboard_token(authorization_header: str | None, expected_token: str) -> bool:
    """Confere o token do painel (`DASHBOARD_API_TOKEN`); vazio nega tudo."""
    return is_valid_bearer_token(authorization_header, expected_token)
