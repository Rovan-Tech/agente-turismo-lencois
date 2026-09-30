"""Aplicação FastAPI: middlewares, rotas e handlers de erro globais."""

import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import conversations, tours, webhook
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Agente de Turismo Lençóis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(tours.router)
app.include_router(conversations.router)


def _sanitize_for_json(value: object) -> object:
    """Troca `inf`/`nan` por `None` — não são JSON válido (RFC 8259) e travariam o encoder."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devolve 422 mesmo quando o payload rejeitado tinha `inf`/`nan` (senão o encoder quebra).

    Reproduz o formato padrão do FastAPI (``jsonable_encoder`` primeiro, pra lidar com `ctx`/`input`
    não serializáveis como `ValueError` de `@field_validator` ou `Decimal`) e só depois sanitiza
    `inf`/`nan`, que sobrevivem ao `jsonable_encoder` por serem `float` válidos em Python.
    """
    content = _sanitize_for_json(jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": content})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
