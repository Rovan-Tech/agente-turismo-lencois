"""Respostas de erro documentadas no OpenAPI (parâmetro `responses=` das rotas).

Cada rota lista os status que devolve com chave literal (`responses={404: NOT_FOUND}`), de modo que
o contrato e a análise estática enxerguem cada `HTTPException` que ela pode levantar.
"""

from __future__ import annotations

from pydantic import BaseModel

TOUR_NOT_FOUND = "passeio não encontrado"
CONVERSATION_NOT_FOUND = "conversa não encontrada"


class ErrorBody(BaseModel):
    """Corpo dos erros levantados com `HTTPException(detail="...")`."""

    detail: str


class ValidationErrorItem(BaseModel):
    """Um erro de validação: o mesmo formato (sem o valor enviado) do 422 do FastAPI."""

    type: str
    loc: list[str | int]
    msg: str


class ValidationErrorBody(BaseModel):
    """Corpo do 422: lista de erros de validação."""

    detail: list[ValidationErrorItem]


BAD_REQUEST: dict[str, object] = {"model": ErrorBody, "description": "Requisição inválida"}
FORBIDDEN: dict[str, object] = {"model": ErrorBody, "description": "Acesso negado"}
NOT_FOUND: dict[str, object] = {"model": ErrorBody, "description": "Recurso não encontrado"}
CONFLICT: dict[str, object] = {"model": ErrorBody, "description": "Conflito com o estado atual"}
PAYLOAD_TOO_LARGE: dict[str, object] = {"model": ErrorBody, "description": "Corpo grande demais"}
UNPROCESSABLE: dict[str, object] = {
    "model": ValidationErrorBody,
    "description": "Entrada inválida",
}
SERVICE_UNAVAILABLE: dict[str, object] = {"model": ErrorBody, "description": "Serviço indisponível"}
