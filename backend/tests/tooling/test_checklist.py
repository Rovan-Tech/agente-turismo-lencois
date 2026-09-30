import re
import time

import checklist
import pytest

EN_DASH = chr(0x2013)
TABLE = (
    "| ID | Controle | Requisito | Hoje | Dono | N/A só se |\n"
    "|---|---|---|---|---|---|\n"
    "| GOV-1 | ADR | x | — | reviewer | o diff não altera arquitetura |\n"
    "| GIT-1 | Git | x | — | reviewer | — |\n"
    "| GATE-2 | Gate | x | — | qa | — |\n"
    "| GATE-3 | Cobertura | x | — | qa | não há código novo |\n"
)


@pytest.fixture
def table(tmp_path, monkeypatch):
    path = tmp_path / "checklist.md"
    path.write_text(TABLE, encoding="utf-8")
    monkeypatch.setattr(checklist, "CHECKLIST_FILE", path)
    return path


def test_required_items_filters_by_owner_and_reads_na_permission(table):
    assert checklist.required_items("qa-tester") == {"GATE-2": False, "GATE-3": True}
    assert checklist.required_items("code-reviewer") == {"GOV-1": True, "GIT-1": False}


def test_required_items_fails_closed_for_unknown_agent(table):
    with pytest.raises(checklist.ChecklistEmptyError):
        checklist.required_items("Explore")


def _assert_qa_items_fail_with(error):
    with pytest.raises(error):
        checklist.required_items("qa-tester")


def test_required_items_fails_closed_when_file_is_missing(table):
    table.unlink()

    _assert_qa_items_fail_with(checklist.ChecklistUnreadableError)


def test_required_items_fails_closed_when_file_is_not_utf8(table):
    table.write_bytes(b"\xff\xfe\x00 nao e utf-8")

    _assert_qa_items_fail_with(checklist.ChecklistUnreadableError)


def test_required_items_fails_closed_on_unknown_owner(table):
    table.write_text(TABLE + "| GATE-9 | Gate | x | — | Reviewer | — |\n", encoding="utf-8")

    _assert_qa_items_fail_with(checklist.ChecklistMalformedError)


def test_required_items_fails_closed_on_row_with_missing_columns(table):
    table.write_text(TABLE + "| GATE-9 | Gate | x | qa |\n", encoding="utf-8")

    _assert_qa_items_fail_with(checklist.ChecklistMalformedError)


def test_validate_reports_problem_instead_of_passing_when_table_is_unreadable(table):
    table.unlink()

    result = checklist.validate("qa-tester", "GATE-2: OK — gate completo verde")

    assert any("ilegível" in problem for problem in result.problems)


def test_validate_reports_problem_when_table_has_no_items_for_agent(table):
    table.write_text("| ID | Dono |\n|---|---|\n", encoding="utf-8")

    result = checklist.validate("qa-tester", "GATE-2: OK — gate completo verde")

    assert any("sem itens" in problem for problem in result.problems)


@pytest.mark.parametrize(
    "line",
    [
        "GATE-2: OK — gate completo verde",
        f"- GATE-2: OK {EN_DASH} gate completo verde",
        "* **GATE-2**: OK - gate completo verde",
    ],
)
def test_parse_items_accepts_common_bullet_and_dash_styles(line):
    items, repeated = checklist.parse_items(line)

    assert items == {"GATE-2": ("OK", "gate completo verde")}
    assert repeated == []


def test_parse_items_reports_repeated_ids():
    _items, repeated = checklist.parse_items("GATE-2: OK — a\nGATE-2: FALHA — b")

    assert repeated == ["GATE-2"]


def test_validate_counts_statuses_and_flags_failure(table):
    message = "GATE-2: OK — gate completo verde\nGATE-3: FALHA — cobertura do diff 70% em a.py:1\n"

    result = checklist.validate("qa-tester", message)

    assert result.counts == {"OK": 1, "N/A": 0, "FALHA": 1}
    assert result.failed
    assert result.problems == []


def test_validate_reports_missing_and_repeated_items(table):
    message = "GATE-2: OK — primeira vez\nGATE-2: OK — duplicado de propósito\n"

    text = " | ".join(checklist.validate("qa-tester", message).problems)

    assert "GATE-3" in text
    assert "repetidos" in text


@pytest.mark.parametrize(("note", "accepted"), [("1234567", False), ("12345678", True)])
def test_validate_requires_at_least_eight_characters_of_evidence(table, note, accepted):
    message = f"GATE-2: OK — {note}\nGATE-3: OK — cobertura 95% no diff\n"

    problems = checklist.validate("qa-tester", message).problems

    assert (problems == []) is accepted


def test_validate_refuses_na_where_the_table_does_not_allow_it(table):
    message = "GATE-2: N/A — não consegui verificar\nGATE-3: N/A — diff sem código novo\n"

    text = " | ".join(checklist.validate("qa-tester", message).problems)

    assert "N/A não permitido" in text
    assert "GATE-2" in text
    assert "GATE-3" not in text


@pytest.mark.parametrize(
    ("agent", "line"),
    [
        ("qa-tester", "Gates: lint ❌"),
        ("qa-tester", "[❌] critério 1 não atendido"),
        ("qa-tester", "- ❌ critério 1 não atendido"),
        ("qa-tester", "1. [❌] critério 1 não atendido"),
        ("qa-tester", "Bugs: [ALTO] quebra ao salvar"),
        ("qa-tester", "**[CRÍTICO]** perda de dados"),
        ("qa-tester", "[CRÍTICO] bug grave"),
        ("qa-tester", "[ALTO] bug grave"),
        ("qa-tester", "[MÉDIO] bug"),
        ("qa-tester", "[MEDIO] bug sem acento"),
        ("qa-tester", "[Alto] bug em minúsculas"),
        ("code-reviewer", "[BLOQUEANTE] a.py:1 — segredo"),
        ("code-reviewer", "- [IMPORTANTE] a.py:1 — falta teste"),
        ("code-reviewer", "[importante] a.py:1 — falta teste"),
    ],
)
def test_contradictions_detects_each_form_on_its_own(table, agent, line):
    result = checklist.ChecklistResult()

    assert len(checklist.contradictions(agent, line, result)) == 1


@pytest.mark.parametrize("padding", ["\n" * 20_000, " " * 50_000, "\t\n " * 10_000])
def test_contradictions_runs_in_linear_time_on_hostile_whitespace(table, padding):
    message = padding + "[ALTO] bug\n" + padding + "Gates: ok"
    started = time.monotonic()

    reasons = checklist.contradictions("qa-tester", message, checklist.ChecklistResult())

    assert len(reasons) == 1
    assert time.monotonic() - started < 1.0


def test_contradictions_reports_failed_items(table):
    result = checklist.ChecklistResult(counts={"OK": 0, "N/A": 0, "FALHA": 2}, failed=True)

    reasons = checklist.contradictions("qa-tester", "Bugs: nenhum", result)

    assert reasons == ["2 item(ns) do checklist em FALHA"]


@pytest.mark.parametrize(
    ("agent", "line"),
    [
        ("qa-tester", "[BAIXO] detalhe cosmético"),
        ("qa-tester", "[BLOQUEANTE] tag de outro agente"),
        ("code-reviewer", "[SUGESTÃO] renomear variável"),
        ("code-reviewer", "[ALTO] tag de outro agente"),
        ("code-reviewer", "Gates: tudo ✅"),
        ("qa-tester", "[✅] critério 1 — verificado"),
    ],
)
def test_contradictions_ignores_non_blocking_lines(table, agent, line):
    assert checklist.contradictions(agent, line, checklist.ChecklistResult()) == []


def test_real_checklist_document_is_well_formed():
    """A tabela oficial: IDs únicos, 6 colunas, dono válido e itens para os dois agentes."""
    text = checklist.CHECKLIST_FILE.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if checklist.ROW_RE.match(line)]
    cells = [[c.strip() for c in line.strip().strip("|").split("|")] for line in rows]
    ids = [row[0] for row in cells]

    assert len(ids) == len(set(ids))
    assert {len(row) for row in cells} == {6}
    assert {row[checklist.OWNER_CELL] for row in cells} == {"reviewer", "qa"}
    assert checklist.required_items("code-reviewer")
    assert checklist.required_items("qa-tester")


def test_real_checklist_every_pending_item_cites_an_existing_tech_debt():
    root = checklist.CHECKLIST_FILE.parents[1]
    debt = (root / "docs" / "tech-debt.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| (TD-[A-Z]\d+) \|", debt, re.M))
    rows = checklist.CHECKLIST_FILE.read_text(encoding="utf-8").splitlines()
    pending = [ln for ln in rows if checklist.ROW_RE.match(ln) and "⏳" in ln]

    assert pending
    assert all(set(re.findall(r"TD-[A-Z]\d+", ln)) & defined for ln in pending)
