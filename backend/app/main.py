"""Aplicação FastAPI: middlewares, rotas e handlers de erro globais."""

import logging
import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import conversations, ingest, tours, webhook
from app.core.config import Settings, get_settings

settings = get_settings()


def _configure_app_logging() -> None:
    """Faz os INFO do `app` saírem: o uvicorn só configura os próprios loggers."""
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        app_logger.addHandler(handler)


_configure_app_logging()


def _sanitize_for_json(value: object) -> object:
    """Troca `inf`/`nan` por `None` — não são JSON válido (RFC 8259) e travariam o encoder."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    return value


async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devolve 422 mesmo quando o payload rejeitado tinha `inf`/`nan` (senão o encoder quebra).

    Reproduz o formato padrão do FastAPI (``jsonable_encoder`` primeiro, pra lidar com `ctx`/`input`
    não serializáveis como `ValueError` de `@field_validator` ou `Decimal`) e só depois sanitiza
    `inf`/`nan`, que sobrevivem ao `jsonable_encoder` por serem `float` válidos em Python.
    """
    content = _sanitize_for_json(jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": content})


async def health() -> dict:
    return {"status": "ok"}


def create_app(settings: Settings) -> FastAPI:
    """Monta a aplicação; recebe a configuração para o CORS poder ser testado em cada modo."""
    application = FastAPI(title="Agente de Turismo Lençóis")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.browser_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    application.include_router(webhook.router)
    application.include_router(tours.router)
    application.include_router(conversations.router)
    application.include_router(ingest.router)
    application.exception_handler(RequestValidationError)(_handle_validation_error)
    application.add_api_route("/health", health, methods=["GET"])
    return application


app = create_app(settings)
