"""Apoio compartilhado dos testes do endpoint de entrada do n8n e do expurgo de conversas."""

import pytest
from httpx import AsyncClient, Response

# Valor de teste do token do n8n (o nome evita falso positivo de "senha fixa" no lint).
INGEST_BEARER = "test-ingest-bearer"
INGEST_URL = "/api/ingest/atendimentos"


def valid_payload(**overrides: object) -> dict[str, object]:
    """Atendimento válido: o que o n8n manda depois de responder ao turista."""
    payload: dict[str, object] = {
        "whatsapp_message_id": "wamid.teste-1",
        "telefone": "5598900000001",
        "texto": "Vou com minha avó de 78 anos, qual passeio indicam?",
        "resposta": "O passeio de bugre pela orla é o mais tranquilo.",
        "idioma": "pt",
        "passeio_sugerido_id": None,
        "precisa_atencao_humana": False,
    }
    payload.update(overrides)
    return payload


def ingest_headers(bearer: str = INGEST_BEARER) -> dict[str, str]:
    """Cabeçalho do n8n: sobrepõe o token do painel que o `client` de teste já envia."""
    return {"Authorization": f"Bearer {bearer}"}


async def post_exchange(
    client: AsyncClient, *, headers: dict[str, str] | None = None, **overrides: object
) -> Response:
    """Envia um atendimento válido (campos trocados por `overrides`) com o token do n8n."""
    return await client.post(
        INGEST_URL, json=valid_payload(**overrides), headers=headers or ingest_headers()
    )


def app_log_text(caplog: pytest.LogCaptureFixture, loggers: tuple[str, ...] = ("app",)) -> str:
    """Tudo que a aplicação (e os `loggers` extras) registrou, sem logs de bibliotecas de teste.

    O `aiosqlite` loga os parâmetros do SQL em DEBUG: isso é do ambiente de teste, não do código.
    """
    return "\n".join(
        f"{r.getMessage()} {vars(r)}" for r in caplog.records if r.name.startswith(loggers)
    )
