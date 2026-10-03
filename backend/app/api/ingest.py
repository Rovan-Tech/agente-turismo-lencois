"""Rota de entrada do n8n: registra no banco os atendimentos que ele já respondeu (ADR-0005)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import Annotated, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_ingest_auth
from app.api.errors import PAYLOAD_TOO_LARGE, SERVICE_UNAVAILABLE, UNPROCESSABLE
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services import handoff, tour_catalog
from app.services import ingest as ingest_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ingest", tags=["ingest"], dependencies=[Depends(require_ingest_auth)]
)

MAX_BODY_BYTES = 16 * 1024

# NUL não existe em texto de WhatsApp e o Postgres o recusa: barrar aqui evita um erro de banco.
_NO_NUL = r"^[^\x00]*$"
_PHONE = r"^[0-9]{8,15}$"
# Texto entre 1 e 4096 (o teto de uma mensagem do WhatsApp), sem espaços nas pontas.
_Text = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4096, pattern=_NO_NUL),
]


class InboundPayload(BaseModel):
    """Mensagem do turista que o n8n só registra (sem resposta da IA, ADR-0008)."""

    # strict: tipos trocados ("true", 1) são erro, não conversão. forbid: campo desconhecido é 422.
    model_config = ConfigDict(strict=True, extra="forbid")

    whatsapp_message_id: str = Field(min_length=1, max_length=128, pattern=_NO_NUL)
    telefone: str = Field(pattern=_PHONE)
    texto: _Text
    idioma: Literal["pt", "en", "es"] | None


class HandlingQuery(BaseModel):
    """Pergunta do n8n sobre quem responde a um telefone (só o telefone, no corpo)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    telefone: str = Field(pattern=_PHONE)


class ExchangePayload(InboundPayload):
    """Atendimento enviado pelo n8n; os nomes são os da saída do Gemini no fluxo."""

    resposta: _Text
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


_T = TypeVar("_T")
_Payload = TypeVar("_Payload", bound=BaseModel)


async def _guarded(operation: Awaitable[_T]) -> _T:
    """Roda a operação de banco; se falhar vira 503 (o n8n tenta de novo, e repetir é seguro)."""
    try:
        return await operation
    except (SQLAlchemyError, OSError) as error:
        # O texto da exceção traz os parâmetros do SQL (telefone e conversa): só o tipo vai ao log.
        # `OSError`: com o banco fora do ar o asyncpg levanta ConnectionRefusedError.
        logger.exception(
            "falha de banco no ingest: %s",
            type(error).__name__,
            exc_info=False,
            extra={"event": "ingest_db_error", "error_type": type(error).__name__},
        )
        raise HTTPException(status_code=503, detail="banco indisponível") from None


async def _parse(request: Request, model: type[_Payload]) -> _Payload:
    """Lê o corpo com teto e o valida; o 422 nunca devolve os valores enviados."""
    body = await _read_limited_body(request)
    try:
        return model.model_validate_json(body)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=_safe_errors(error)) from None


@router.post(
    "/atendimentos",
    responses={413: PAYLOAD_TOO_LARGE, 422: UNPROCESSABLE, 503: SERVICE_UNAVAILABLE},
)
async def record_exchange(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Grava o atendimento (mensagem do turista e resposta enviada), uma vez por mensagem da Meta.

    O corpo é lido e validado aqui, e não pelo FastAPI, para recusar o excesso de tamanho antes de
    processar e para o 422 nunca devolver os valores enviados. Só o resultado vai ao log.

    Raises:
        HTTPException: 413 se o corpo passar de 16 KiB; 422 se o contrato não for cumprido; 503 se o
            banco falhar (o n8n tenta de novo, e repetir é seguro).
    """
    payload = await _parse(request, ExchangePayload)
    recorded = await _guarded(ingest_service.record_exchange(db, _to_exchange(payload)))
    outcome = "criado" if recorded.created else "duplicado"
    logger.info(
        "atendimento do n8n: %s", outcome, extra={"event": "ingest_exchange", "outcome": outcome}
    )
    return {"status": outcome, "conversa_id": recorded.conversation_id}


@router.post(
    "/mensagens",
    responses={413: PAYLOAD_TOO_LARGE, 422: UNPROCESSABLE, 503: SERVICE_UNAVAILABLE},
)
async def record_inbound(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Grava só a mensagem do turista, sem resposta: o n8n usa quando uma pessoa está atendendo.

    Raises:
        HTTPException: 413 se o corpo passar de 16 KiB; 422 se o contrato não for cumprido; 503 se o
            banco falhar (o n8n tenta de novo, e repetir é seguro).
    """
    payload = await _parse(request, InboundPayload)
    inbound = ingest_service.Inbound(
        payload.whatsapp_message_id, payload.telefone, payload.texto, payload.idioma
    )
    recorded = await _guarded(ingest_service.record_inbound(db, inbound))
    outcome = "criado" if recorded.created else "duplicado"
    logger.info(
        "mensagem do turista (atendimento humano): %s",
        outcome,
        extra={"event": "ingest_inbound", "outcome": outcome},
    )
    return {"status": outcome, "conversa_id": recorded.conversation_id}


@router.post(
    "/conversas/atendimento",
    responses={413: PAYLOAD_TOO_LARGE, 422: UNPROCESSABLE, 503: SERVICE_UNAVAILABLE},
)
async def conversation_handling(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Diz ao n8n quem responde a este telefone: `ia` ou `humano` (então ele só registra).

    É um POST só para o telefone ir no corpo: na URL ele cairia no log de acesso do servidor.
    Um telefone sem conversa aberta é `ia`. Não grava nada.
    """
    payload = await _parse(request, HandlingQuery)
    handling = await _guarded(handoff.handling_for_phone(db, settings, payload.telefone))
    return {"atendimento": handling.value}


@router.get("/catalogo")
async def tour_catalog_for_n8n(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    """Passeios ativos para o n8n montar a resposta ao turista (mesmos campos que iam ao LLM).

    O n8n lia o catálogo em `/api/tours` com o token do painel; com o painel só no login do Access
    esse token não vale mais, então o n8n lê aqui, com o próprio `INGEST_API_TOKEN`. Só os campos
    do catálogo: sem capacidade diária nem estado, que são da gestão do painel.
    """
    tours = await tour_catalog.list_tours(db, incluir_inativos=False)
    return [tour.to_catalog_dict() for tour in tours]
