"""Rota de entrada do n8n: registra no banco os atendimentos que ele já respondeu (ADR-0005)."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_ingest_auth
from app.db.session import get_db
from app.services import ingest as ingest_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ingest", tags=["ingest"], dependencies=[Depends(require_ingest_auth)]
)

MAX_BODY_BYTES = 16 * 1024

# NUL não existe em texto de WhatsApp e o Postgres o recusa: barrar aqui evita um erro de banco.
_NO_NUL = r"^[^\x00]*$"
# Texto entre 1 e 4096 (o teto de uma mensagem do WhatsApp), sem espaços nas pontas.
_Text = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4096, pattern=_NO_NUL),
]


class ExchangePayload(BaseModel):
    """Atendimento enviado pelo n8n; os nomes são os da saída do Gemini no fluxo."""

    # strict: tipos trocados ("true", 1) são erro, não conversão. forbid: campo desconhecido é 422.
    model_config = ConfigDict(strict=True, extra="forbid")

    whatsapp_message_id: str = Field(min_length=1, max_length=128, pattern=_NO_NUL)
    telefone: str = Field(pattern=r"^[0-9]{8,15}$")
    texto: _Text
    resposta: _Text
    idioma: Literal["pt", "en", "es"] | None
    passeio_sugerido_id: str | None = Field(max_length=128, pattern=_NO_NUL)
    precisa_atencao_humana: bool


async def _read_limited_body(request: Request) -> bytes:
    """Lê o corpo com teto: recusa antes de guardar tudo na memória se passar de 16 KiB."""
    declared = request.headers.get("content-length", "")
    if declared.isascii() and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="corpo grande demais")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="corpo grande demais")
    return bytes(body)


def _safe_errors(error: ValidationError) -> list[dict[str, object]]:
    """Erros de validação sem o valor enviado: o padrão do FastAPI ecoaria telefone e texto."""
    return [
        {"type": item["type"], "loc": list(item["loc"]), "msg": item["msg"]}
        for item in error.errors(include_url=False, include_context=False, include_input=False)
    ]


def _to_exchange(payload: ExchangePayload) -> ingest_service.Exchange:
    return ingest_service.Exchange(
        message_id=payload.whatsapp_message_id,
        phone=payload.telefone,
        text=payload.texto,
        reply=payload.resposta,
        language=payload.idioma,
        suggested_tour_id=payload.passeio_sugerido_id,
        needs_human=payload.precisa_atencao_humana,
    )


@router.post("/atendimentos")
async def record_exchange(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Grava o atendimento (mensagem do turista e resposta enviada), uma vez por mensagem da Meta.

    O corpo é lido e validado aqui, e não pelo FastAPI, para recusar o excesso de tamanho antes de
    processar e para o 422 nunca devolver os valores enviados. Só o resultado vai ao log.

    Raises:
        HTTPException: 413 se o corpo passar de 16 KiB; 422 se o contrato não for cumprido; 503 se o
            banco falhar (o n8n tenta de novo, e repetir é seguro).
    """
    body = await _read_limited_body(request)
    try:
        payload = ExchangePayload.model_validate_json(body)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=_safe_errors(error)) from None

    try:
        recorded = await ingest_service.record_exchange(db, _to_exchange(payload))
    except (SQLAlchemyError, OSError) as error:
        # O texto da exceção traz os parâmetros do SQL (telefone e conversa): só o tipo vai ao log.
        # `OSError`: com o banco fora do ar o asyncpg levanta ConnectionRefusedError.
        logger.exception(
            "falha de banco ao registrar atendimento: %s",
            type(error).__name__,
            exc_info=False,
            extra={"event": "ingest_db_error", "error_type": type(error).__name__},
        )
        raise HTTPException(status_code=503, detail="banco indisponível") from None
    outcome = "criado" if recorded.created else "duplicado"
    logger.info(
        "atendimento do n8n: %s", outcome, extra={"event": "ingest_exchange", "outcome": outcome}
    )
    return {"status": outcome, "conversa_id": recorded.conversation_id}
