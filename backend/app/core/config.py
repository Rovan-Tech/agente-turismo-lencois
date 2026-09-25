from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Parâmetros de query que só drivers baseados em libpq (psycopg2) entendem — o Neon inclui
# `channel_binding` nas connection strings por padrão, mas o asyncpg quebra com
# "TypeError: connect() got an unexpected keyword argument 'channel_binding'" se ele chegar.
_ASYNCPG_UNSUPPORTED_QUERY_PARAMS = {"channel_binding"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./local.db"

    @field_validator("database_url")
    @classmethod
    def _strip_asyncpg_unsupported_params(cls, value: str) -> str:
        parsed = urlparse(value)
        if not parsed.query:
            return value
        query = [
            (k, v) for k, v in parse_qsl(parsed.query) if k not in _ASYNCPG_UNSUPPORTED_QUERY_PARAMS
        ]
        return urlunparse(parsed._replace(query=urlencode(query)))

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "changeme"
    whatsapp_app_secret: str = ""
    whatsapp_api_base_url: str = "https://graph.facebook.com/v21.0"

    whisper_model_size: str = "base"

    agency_name: str = "Agência de Turismo em Lençóis"
    frontend_origin: str = "http://localhost:5173"
    dashboard_api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
