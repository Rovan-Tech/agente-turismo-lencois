from app.core.config import Settings
from app.db.session import get_connect_args


def test_strips_channel_binding_and_sslmode_from_neon_url():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@host/db?sslmode=require&channel_binding=require"
    )
    assert "channel_binding" not in settings.database_url
    assert "sslmode" not in settings.database_url
    assert settings.database_url == "postgresql+asyncpg://user:pass@host/db"


def test_leaves_url_without_query_untouched():
    settings = Settings(database_url="sqlite+aiosqlite:///./local.db")
    assert settings.database_url == "sqlite+aiosqlite:///./local.db"


def test_leaves_unrelated_query_params_untouched():
    settings = Settings(database_url="postgresql+asyncpg://user:pass@host/db?application_name=api")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host/db?application_name=api"


def test_connect_args_requests_ssl_for_asyncpg():
    assert get_connect_args("postgresql+asyncpg://user:pass@host/db") == {"ssl": True}


def test_connect_args_empty_for_sqlite():
    assert get_connect_args("sqlite+aiosqlite:///./local.db") == {}
