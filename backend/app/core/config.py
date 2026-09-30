from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Parâmetros de query que só drivers baseados em libpq (psycopg2) entendem quando embutidos numa
# URL. O SQLAlchemy repassa qualquer parâmetro que não reconhece como kwarg cru pro
# `asyncpg.connect()`, que não aceita nem `sslmode` nem `channel_binding` (só aceita `ssl=`) —
# ambos quebram com "TypeError: connect() got an unexpected keyword argument '...'". O Neon
# inclui os dois por padrão nas connection strings que fornece. SSL é configurado à parte via
# `connect_args` (ver app/db/session.py), não pela query string.
_ASYNCPG_UNSUPPORTED_QUERY_PARAMS = {"channel_binding", "sslmode"}


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
    # Teto do áudio baixado da Meta antes de transcrever: uma mensagem de voz normal (Opus) fica
    # bem abaixo disso, e acima dele o Whisper ocuparia a instância do Cloud Run à toa.
    max_audio_bytes: int = 5 * 1024 * 1024

    agency_name: str = "Agência de Turismo em Lençóis"
    frontend_origin: str = "http://localhost:5173"
    dashboard_api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
