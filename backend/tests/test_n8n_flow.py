"""O fluxo do n8n exportado em `docs/n8n/` cumpre o que o ADR-0008 promete (somente leitura).

O n8n é publicado à mão: um reexport pode quebrar uma ligação ou um corpo sem que nada no backend
perceba. Estes testes leem o JSON e garantem o contrato com o backend e o caminho de cada estado.
"""

import json
import re
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from app.api.ingest import ExchangePayload, HandlingQuery, InboundPayload

FLOW_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "n8n" / "agente-turismo-whatsapp.workflow.json"
)
LOOKUP = "Consultar atendimento"
BRANCH = "Uma pessoa está atendendo?"
HUMAN_ONLY = "Registrar mensagem (atendente ativo)"
CATALOG = "Buscar catálogo de passeios"
CONTINGENCY = "Enviar aviso de contingência"
Flow = dict[str, Any]  # JSON exportado pelo n8n: o esquema é do n8n, não nosso
SENDS_OR_THINKS = ("n8n-nodes-base.whatsApp", "@n8n/n8n-nodes-langchain.chainLlm")


@pytest.fixture(scope="module")
def flow() -> Flow:
    loaded: Flow = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    return loaded


def _node(flow: Flow, name: str) -> Flow:
    return next(node for node in flow["nodes"] if node["name"] == name)


def _targets(flow: Flow, source: str, output: int) -> list[str]:
    outputs = flow["connections"].get(source, {}).get("main", [])
    return [link["node"] for link in outputs[output]] if output < len(outputs) else []


def _successors(flow: Flow, node: str) -> set[str]:
    outputs = flow["connections"].get(node, {}).get("main", [])
    return {link["node"] for output in outputs for link in output}


def _reachable(flow: Flow, start: str) -> set[str]:
    seen, queue = {start}, deque([start])
    while queue:
        new = _successors(flow, queue.popleft()) - seen
        seen |= new
        queue.extend(new)
    return seen


def _body_keys(node: Flow) -> set[str]:
    body = node["parameters"]["jsonBody"]
    return set(re.findall(r"(?:^|\{)\s*(\w+):", body, flags=re.MULTILINE))


def test_lookup_runs_before_the_model_and_a_failure_goes_to_the_contingency(flow):
    lookup = _node(flow, LOOKUP)

    assert _targets(flow, "Só mensagens de texto", 0) == [LOOKUP]
    assert lookup["onError"] == "continueErrorOutput"
    assert _targets(flow, LOOKUP, 0) == [BRANCH]
    assert _targets(flow, LOOKUP, 1) == [CONTINGENCY]
    assert lookup["retryOnFail"] is True
    assert lookup["parameters"]["options"]["timeout"] <= 5000


def test_a_person_attending_only_records_the_message_and_never_reaches_the_model_or_a_send(flow):
    assert _targets(flow, BRANCH, 0) == [HUMAN_ONLY]

    reached = _reachable(flow, HUMAN_ONLY)

    assert reached == {HUMAN_ONLY}
    assert not {n["name"] for n in flow["nodes"] if n["type"] in SENDS_OR_THINKS} & reached


def test_the_ai_branch_goes_on_to_the_catalog_and_the_model(flow):
    assert _targets(flow, BRANCH, 1) == [CATALOG]
    assert "Gerar resposta do turismo" in _reachable(flow, CATALOG)


def test_the_branch_checks_for_exactly_the_human_state(flow):
    [condition] = _node(flow, BRANCH)["parameters"]["conditions"]["conditions"]

    assert condition["leftValue"] == "={{ $json.atendimento }}"
    assert condition["rightValue"] == "humano"
    assert condition["operator"]["operation"] == "equals"


@pytest.mark.parametrize(
    ("node", "model"),
    [
        (LOOKUP, HandlingQuery),
        (HUMAN_ONLY, InboundPayload),
        ("Registrar atendimento no painel", ExchangePayload),
        ("Registrar atendimento (contingência)", ExchangePayload),
    ],
    ids=["lookup", "inbound_only", "exchange", "exchange_contingency"],
)
def test_each_request_body_has_exactly_the_fields_the_backend_contract_requires(flow, node, model):
    assert _body_keys(_node(flow, node)) == set(model.model_fields)


@pytest.mark.parametrize("node", [LOOKUP, HUMAN_ONLY, CATALOG])
def test_the_new_requests_use_the_ingest_credential_and_the_backend_placeholder(flow, node):
    parameters = _node(flow, node)["parameters"]

    assert parameters["url"].startswith("<BACKEND_URL>/api/ingest/")
    assert _node(flow, node)["credentials"] == {
        "httpTemplatedCustomAuth": {"name": "Ingest API Token account"}
    }


def test_the_export_carries_no_credential_id_webhook_id_or_token(flow):
    text = FLOW_PATH.read_text(encoding="utf-8")
    credentials = [c for node in flow["nodes"] for c in node.get("credentials", {}).values()]

    assert all(set(credential) == {"name"} for credential in credentials)
    assert not any("webhookId" in node for node in flow["nodes"])
    assert "Bearer " not in text


REGISTRATIONS = [
    HUMAN_ONLY,
    "Registrar atendimento no painel",
    "Registrar atendimento (contingência)",
]


@pytest.mark.parametrize("node", REGISTRATIONS)
def test_registrations_send_the_whatsapp_profile_name_as_an_optional_nullable_field(flow, node):
    body = _node(flow, node)["parameters"]["jsonBody"]

    assert "cliente_nome" in _body_keys(_node(flow, node))
    assert "contacts?.[0]?.profile?.name" in body
    assert "|| null" in body
    assert ".slice(0, 100)" in body


def test_the_profile_name_never_reaches_the_model_prompt(flow):
    """LGPD: nome é dado pessoal; o Gemini só recebe o texto do turista e o catálogo."""
    model_side = [
        node
        for node in flow["nodes"]
        if node["name"] in {"Preparar entrada do modelo", "Gerar resposta do turismo"}
        or node["type"].startswith("@n8n/n8n-nodes-langchain.")
    ]

    assert model_side
    for node in model_side:
        text = json.dumps(node["parameters"], ensure_ascii=False)
        assert "contacts" not in text
        assert "profile" not in text
        assert "cliente_nome" not in text
