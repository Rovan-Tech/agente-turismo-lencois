"""Configuração da aplicação, lida de variáveis de ambiente (pydantic-settings)."""

import re
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Parâmetros de query que só drivers baseados em libpq (psycopg2) entendem quando embutidos numa
# URL. O SQLAlchemy repassa qualquer parâmetro que não reconhece como kwarg cru pro
# `asyncpg.connect()`, que não aceita nem `sslmode` nem `channel_binding` (só aceita `ssl=`) —
# ambos quebram com "TypeError: connect() got an unexpected keyword argument '...'". O Neon
# inclui os dois por padrão nas connection strings que fornece. SSL é configurado à parte via
# `connect_args` (ver app/db/session.py), não pela query string.
_ASYNCPG_UNSUPPORTED_QUERY_PARAMS = {"channel_binding", "sslmode"}


class Settings(BaseSettings):
    # hide_input_in_errors: o erro de validação não imprime os valores lidos (poderiam ser tokens).
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

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
    # Token do n8n para registrar atendimentos (ADR-0005). Próprio e distinto do token do painel:
    # este vai no bundle público e só pode proteger leitura. Vazio = rota fechada (401 sempre).
    ingest_api_token: str = ""
    # Conversa sem atividade há mais que isso é apagada com as mensagens (LGPD, ADR-0005).
    # Mínimo de 1: com 0 ou negativo o corte cairia no futuro e o expurgo apagaria tudo.
    conversation_retention_days: int = Field(default=90, ge=1)

    # Login do painel (ADR-0006). `token`: só o token fixo (como hoje). `both`: token fixo ou JWT do
    # Cloudflare Access, para testar. `access`: só o JWT. Sem `ACCESS_*`, o JWT é sempre recusado.
    panel_auth_mode: Literal["token", "both", "access"] = "token"
    access_team_domain: str = ""  # https://<equipe>.cloudflareaccess.com
    access_aud: str = ""  # "Application Audience (AUD) tag" do aplicativo no Access

    @field_validator("access_team_domain")
    @classmethod
    def _access_team_domain_must_be_a_cloudflare_team_url(cls, value: str) -> str:
        if value and not re.fullmatch(r"https://[a-z0-9-]+\.cloudflareaccess\.com", value):
            msg = "ACCESS_TEAM_DOMAIN deve ser https://<equipe>.cloudflareaccess.com"
            raise ValueError(msg)
        return value

    @property
    def browser_origins(self) -> list[str]:
        """Origens de navegador aceitas no CORS.

        Nenhuma no modo `access`: o painel fala com a API pela própria origem (proxy do Pages) e
        nunca direto com o Cloud Run.
        """
        return [] if self.panel_auth_mode == "access" else [self.frontend_origin]

    @model_validator(mode="after")
    def _ingest_token_must_differ_from_dashboard_token(self) -> "Settings":
        if self.ingest_api_token and self.ingest_api_token == self.dashboard_api_token:
            msg = (
                "INGEST_API_TOKEN deve ser diferente de DASHBOARD_API_TOKEN (o do painel é público)"
            )
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
