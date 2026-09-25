from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./local.db"

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
