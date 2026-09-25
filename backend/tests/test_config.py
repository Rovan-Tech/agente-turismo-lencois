from app.core.config import Settings


def test_strips_channel_binding_from_neon_url():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@host/db?sslmode=require&channel_binding=require"
    )
    assert "channel_binding" not in settings.database_url
    assert "sslmode=require" in settings.database_url


def test_leaves_url_without_query_untouched():
    settings = Settings(database_url="sqlite+aiosqlite:///./local.db")
    assert settings.database_url == "sqlite+aiosqlite:///./local.db"


def test_leaves_supported_query_params_untouched():
    settings = Settings(database_url="postgresql+asyncpg://user:pass@host/db?sslmode=require")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host/db?sslmode=require"
