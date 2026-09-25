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


def is_valid_dashboard_token(authorization_header: str | None, expected_token: str) -> bool:
    if not expected_token:
        return False
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    received = authorization_header.removeprefix("Bearer ")
    return hmac.compare_digest(received, expected_token)
