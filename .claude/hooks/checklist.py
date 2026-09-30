"""Validação do checklist de engenharia no relatório dos subagents (code-reviewer, qa-tester).

A fonte dos itens é a tabela de `docs/checklist-engenharia.md`: um item novo lá passa a ser exigido
automaticamente. O relatório precisa ter uma linha `ID: OK|N/A|FALHA — evidência` para cada item do
agente; `N/A` só é aceito nos itens cuja coluna "N/A só se" não é `—`. O veredito `APROVADO` é
incompatível com qualquer `FALHA`, problema BLOQUEANTE/IMPORTANTE (reviewer), bug
CRÍTICO/ALTO/MÉDIO (QA) ou critério/gate marcado com ❌. Se a tabela não puder ser lida, a
validação falha (fail-closed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import hook_common as common

CHECKLIST_FILE = common.PROJECT_DIR / "docs" / "checklist-engenharia.md"
OWNERS = {"code-reviewer": "reviewer", "qa-tester": "qa"}
MIN_NOTE = 8
OWNER_CELL = 4
NA_CELL = 5
NO_NA_MARK = "—"
ROW_RE = re.compile(r"^\|\s*([A-Z]{2,5}-\d+)\s*\|")
DASHES = "".join(chr(code) for code in (0x2014, 0x2013)) + "-"  # travessão, meia-risca, hífen
ITEM_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([A-Z]{2,5}-\d+)(?:\*\*)?\s*:\s*(OK|N/A|FALHA)\b"
    rf"\s*(?:[{DASHES}]+\s*(.*))?$"
)
# Só espaço e tab (nunca \s): evita backtracking em relatórios com milhares de linhas em branco.
LEAD = r"^[ \t]*(?:(?:Problemas|Bugs):[ \t]*)?(?:(?:[-*+]|\d+[.)])[ \t]*)?(?:\*+[ \t]*)?"
BLOCKING_RE = {
    "code-reviewer": re.compile(LEAD + r"\[(BLOQUEANTE|IMPORTANTE)\]", re.M | re.I),
    "qa-tester": re.compile(LEAD + r"\[(CR[ÍI]TICO|ALTO|M[ÉE]DIO)\]", re.M | re.I),
}
FAILED_CRITERION_RE = re.compile(LEAD + r"(?:\[❌\]|❌)", re.M)
FAILED_GATES_RE = re.compile(r"^[ \t]*Gates:.*❌", re.M)
FORMAT_HELP = (
    "Formato: seção `Checklist:` com uma linha por item, `ID: OK — evidência`, "
    "`ID: N/A — justificativa` ou `ID: FALHA — arquivo:linha, problema e correção` "
    f"(mínimo {MIN_NOTE} caracteres de justificativa em todas; `N/A` só nos itens que a tabela "
    "permite). Itens exigidos e condições de N/A: docs/checklist-engenharia.md. "
    "Reenvie o relatório completo pela mesma via (SubagentHandback)."
)


class ChecklistUnavailableError(RuntimeError):
    """A tabela do checklist não pôde ser lida ou não tem itens para o agente."""

    message = "checklist indisponível"

    def __str__(self) -> str:
        """Mensagem fixa da subclasse, sem texto montado no ponto do `raise`."""
        return self.message


class ChecklistUnreadableError(ChecklistUnavailableError):
    """O arquivo do checklist não existe ou não é UTF-8 válido."""

    message = "checklist ilegível (docs/checklist-engenharia.md)"


class ChecklistEmptyError(ChecklistUnavailableError):
    """A tabela não tem nenhum item para o dono do agente (formato alterado?)."""

    message = "checklist sem itens para este agente (tabela alterada ou coluna Dono mudou?)"


class ChecklistMalformedError(ChecklistUnavailableError):
    """Uma linha com ID não tem as 6 colunas da tabela (o item deixaria de ser exigido)."""

    message = "linha malformada na tabela do checklist (esperadas 6 colunas)"


@dataclass
class ChecklistResult:
    """Resultado da leitura do checklist de um relatório."""

    counts: dict[str, int] = field(default_factory=lambda: {"OK": 0, "N/A": 0, "FALHA": 0})
    problems: list[str] = field(default_factory=list)
    failed: bool = False


def required_items(agent: str) -> dict[str, bool]:
    """Itens que `agent` precisa reportar, lidos da tabela do checklist.

    Args:
        agent: Nome do subagent (`code-reviewer` ou `qa-tester`).

    Returns:
        Mapa `ID -> N/A permitido`, na ordem da tabela.

    Raises:
        ChecklistUnavailableError: Se o arquivo for ilegível, tiver linha malformada ou não tiver
            item para o agente (o hook trata como falha, nunca como "nada a verificar").
    """
    owner = OWNERS.get(agent)
    try:
        text = CHECKLIST_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ChecklistUnreadableError from exc
    items: dict[str, bool] = {}
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= NA_CELL:
            raise ChecklistMalformedError
        if cells[OWNER_CELL] not in OWNERS.values():
            raise ChecklistMalformedError
        if cells[OWNER_CELL] == owner:
            items[match.group(1)] = not cells[NA_CELL].startswith(NO_NA_MARK)
    if not items:
        raise ChecklistEmptyError
    return items


def parse_items(message: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Lê as linhas `ID: STATUS — nota` de um relatório.

    Args:
        message: Texto completo do relatório.

    Returns:
        Os itens `ID -> (status, nota)` e a lista de IDs repetidos.
    """
    items: dict[str, tuple[str, str]] = {}
    repeated: list[str] = []
    for line in message.splitlines():
        match = ITEM_RE.match(line)
        if not match:
            continue
        item_id, status, note = match.group(1), match.group(2), (match.group(3) or "").strip()
        if item_id in items:
            repeated.append(item_id)
        items[item_id] = (status, note)
    return items, repeated


def _item_problems(required: dict[str, bool], items: dict[str, tuple[str, str]]) -> list[str]:
    """Problemas de completude, evidência e N/A indevido dos itens exigidos."""
    problems = []
    missing = [i for i in required if i not in items]
    if missing:
        problems.append("faltam os itens do checklist: " + ", ".join(missing))
    weak = [i for i in required if i in items and len(items[i][1]) < MIN_NOTE]
    if weak:
        problems.append("itens sem evidência/justificativa: " + ", ".join(weak))
    forbidden_na = [
        i for i, allowed in required.items() if not allowed and items.get(i, ("",))[0] == "N/A"
    ]
    if forbidden_na:
        problems.append("N/A não permitido pela tabela em: " + ", ".join(forbidden_na))
    return problems


def validate(agent: str, message: str) -> ChecklistResult:
    """Confere o checklist do relatório: itens completos, evidência e N/A permitido.

    Args:
        agent: Nome do subagent que escreveu o relatório.
        message: Texto completo do relatório.

    Returns:
        O resultado com a contagem por status e os problemas encontrados (fail-closed: tabela
        ilegível vira um problema).
    """
    result = ChecklistResult()
    items, repeated = parse_items(message)
    try:
        result.problems.extend(_item_problems(required_items(agent), items))
    except ChecklistUnavailableError as exc:
        result.problems.append(str(exc))
    if repeated:
        result.problems.append("itens repetidos no checklist: " + ", ".join(sorted(set(repeated))))
    for status, _note in items.values():
        result.counts[status] += 1
    result.failed = result.counts["FALHA"] > 0
    return result


def contradictions(agent: str, message: str, result: ChecklistResult) -> list[str]:
    """Motivos pelos quais um relatório `APROVADO` se contradiz.

    Args:
        agent: Nome do subagent que escreveu o relatório.
        message: Texto completo do relatório.
        result: Resultado de `validate` para o mesmo relatório.

    Returns:
        Lista de motivos; vazia quando o `APROVADO` é coerente.
    """
    reasons = []
    if result.failed:
        reasons.append(f"{result.counts['FALHA']} item(ns) do checklist em FALHA")
    blocking = BLOCKING_RE.get(agent)
    if blocking and blocking.search(message):
        reasons.append("há problema/bug bloqueante listado")
    if FAILED_CRITERION_RE.search(message) or FAILED_GATES_RE.search(message):
        reasons.append("há critério de aceite ou gate marcado com ❌")
    return reasons
