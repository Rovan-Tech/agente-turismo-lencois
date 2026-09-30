import pytest
from fastapi import HTTPException

from app.api.deps import require_dashboard_auth
from app.core.config import get_settings

_TEST_BEARER_VALUE = "abc123"


@pytest.fixture
def settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dashboard_api_token", _TEST_BEARER_VALUE)
    return settings


@pytest.mark.asyncio
async def test_require_dashboard_auth_accepts_valid_token(settings):
    await require_dashboard_auth(authorization=f"Bearer {_TEST_BEARER_VALUE}", settings=settings)


@pytest.mark.asyncio
async def test_require_dashboard_auth_rejects_wrong_token(settings):
    with pytest.raises(HTTPException) as exc_info:
        await require_dashboard_auth(authorization="Bearer errado", settings=settings)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_dashboard_auth_rejects_missing_header(settings):
    with pytest.raises(HTTPException) as exc_info:
        await require_dashboard_auth(authorization=None, settings=settings)
    assert exc_info.value.status_code == 401
