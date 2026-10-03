import json
from decimal import Decimal

import pytest
from fastapi.exceptions import RequestValidationError

from app.main import _handle_validation_error, _sanitize_for_json


@pytest.mark.asyncio
async def test_health_returns_ok_status(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sanitize_for_json_replaces_inf_and_nan_recursively():
    sanitized = _sanitize_for_json({"a": [float("inf"), float("nan"), 1.5], "b": "texto"})
    assert sanitized == {"a": [None, None, 1.5], "b": "texto"}


def test_validation_error_handler_survives_non_json_native_ctx():
    # ctx com ValueError (comum em @field_validator) e Decimal (comum em limites de Numeric) —
    # nenhum dos dois é serializável por json.dumps sem passar pelo jsonable_encoder antes.
    errors = [
        {
            "type": "value_error",
            "loc": ("body", "campo"),
            "msg": "erro customizado",
            "input": "x",
            "ctx": {"error": ValueError("motivo"), "limite": Decimal("10")},
        }
    ]
    exc = RequestValidationError(errors)

    # request não é usado pelo handler; None evita montar um Request de verdade só pro teste.
    response = _handle_validation_error(None, exc)  # type: ignore[arg-type]

    assert response.status_code == 422
    body = json.loads(bytes(response.body))
    assert body["detail"][0]["msg"] == "erro customizado"
    assert body["detail"][0]["ctx"]["limite"] == 10


def test_app_logger_emits_info_with_its_own_handler():
    """O uvicorn só configura os próprios loggers: sem isto, os INFO do app nunca saem."""
    import logging

    from app import main

    app_logger = logging.getLogger("app")

    assert main.app.title  # a configuração do logger roda na importação de `app.main`
    assert app_logger.isEnabledFor(logging.INFO)
    assert app_logger.handlers
