import pytest
from pydantic import ValidationError

from app.core.config import Settings


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


def test_max_audio_bytes_defaults_to_five_megabytes(monkeypatch):
    monkeypatch.delenv("MAX_AUDIO_BYTES", raising=False)
    assert Settings(_env_file=None).max_audio_bytes == 5 * 1024 * 1024


def _settings(ingest: str, dashboard: str) -> Settings:
    return Settings.model_validate({"ingest_api_token": ingest, "dashboard_api_token": dashboard})


def test_ingest_token_is_unset_by_default(monkeypatch):
    monkeypatch.delenv("INGEST_API_TOKEN", raising=False)
    assert Settings(_env_file=None).ingest_api_token == ""


def test_conversation_retention_defaults_to_90_days(monkeypatch):
    monkeypatch.delenv("CONVERSATION_RETENTION_DAYS", raising=False)
    assert Settings(_env_file=None).conversation_retention_days == 90


def test_configuration_errors_do_not_print_the_values_read_from_the_environment():
    with pytest.raises(ValidationError) as error:
        _settings("mesmo-valor-9988", "mesmo-valor-9988")

    assert "mesmo-valor-9988" not in str(error.value)


def test_settings_reject_ingest_token_equal_to_dashboard_token():
    with pytest.raises(ValidationError, match="INGEST_API_TOKEN"):
        _settings("mesmo-valor", "mesmo-valor")


@pytest.mark.parametrize(("ingest", "dashboard"), [("um", "outro"), ("", ""), ("um", "")])
def test_settings_accept_distinct_or_unset_tokens(ingest, dashboard):
    assert _settings(ingest, dashboard).ingest_api_token == ingest


@pytest.mark.parametrize("days", [0, -1])
def test_conversation_retention_must_be_at_least_one_day(days):
    with pytest.raises(ValidationError, match="conversation_retention_days"):
        Settings.model_validate({"conversation_retention_days": days})
