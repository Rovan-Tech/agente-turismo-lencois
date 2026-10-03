"""O contrato OpenAPI declara os erros que as rotas levantam com `HTTPException` (TD-C1)."""

import pytest

from app.main import app

# (método, caminho) -> status de erro que a própria rota devolve.
DOCUMENTED_ERRORS = [
    ("get", "/webhook/whatsapp", {"403"}),
    ("post", "/webhook/whatsapp", {"400", "403"}),
    ("get", "/api/tours/{tour_id}/agenda", {"404", "422"}),
    ("get", "/api/tours/{tour_id}/agendamentos", {"404"}),
    ("post", "/api/tours/{tour_id}/agendamentos", {"404", "409"}),
    ("post", "/api/tours", {"409"}),
    ("put", "/api/tours/{tour_id}", {"404"}),
    ("delete", "/api/tours/{tour_id}", {"404"}),
    ("patch", "/api/conversations/{conversation_id}/status", {"404"}),
    ("post", "/api/conversations/{conversation_id}/assumir", {"404"}),
    ("post", "/api/conversations/{conversation_id}/devolver", {"404"}),
    ("post", "/api/conversations/{conversation_id}/mensagens", {"404"}),
    ("get", "/api/conversations/{conversation_id}", {"404"}),
    ("post", "/api/ingest/atendimentos", {"413", "422", "503"}),
    ("post", "/api/ingest/mensagens", {"413", "422", "503"}),
    ("post", "/api/ingest/conversas/atendimento", {"413", "422", "503"}),
]


@pytest.mark.parametrize(("method", "path", "statuses"), DOCUMENTED_ERRORS)
def test_route_documents_the_errors_it_raises(method, path, statuses):
    responses = app.openapi()["paths"][path][method]["responses"]

    assert statuses <= set(responses)


def test_error_responses_use_the_shape_the_api_sends():
    schemas = app.openapi()["components"]["schemas"]

    assert schemas["ErrorBody"]["properties"]["detail"]["type"] == "string"
    assert set(schemas["ValidationErrorItem"]["required"]) == {"type", "loc", "msg"}
