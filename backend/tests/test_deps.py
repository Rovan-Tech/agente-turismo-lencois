import pytest
from fastapi import HTTPException, Request

from app.api.deps import require_dashboard_auth
from app.core.config import Settings, get_settings

_TEST_BEARER_VALUE = "abc123"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = get_settings()
    monkeypatch.setattr(settings, "dashboard_api_token", _TEST_BEARER_VALUE)
    monkeypatch.setattr(settings, "panel_auth_mode", "token")
    return settings


async def _authenticate(settings: Settings, authorization: str | None) -> None:
    """Chama a dependência como o FastAPI chamaria, já com os cabeçalhos extraídos."""
    request = Request({"type": "http", "method": "GET", "headers": [], "path": "/api/tours"})
    await require_dashboard_auth(
        request=request,
        authorization=authorization,
        cf_access_jwt_assertion=None,
        x_panel_request=None,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_require_dashboard_auth_accepts_valid_token(settings):
    await _authenticate(settings, f"Bearer {_TEST_BEARER_VALUE}")


@pytest.mark.asyncio
@pytest.mark.parametrize("authorization", ["Bearer errado", None], ids=["wrong_token", "missing"])
async def test_require_dashboard_auth_rejects_wrong_or_missing_credentials(settings, authorization):
    with pytest.raises(HTTPException) as exc_info:
        await _authenticate(settings, authorization)
    assert exc_info.value.status_code == 401
