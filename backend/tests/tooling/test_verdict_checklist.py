import json

import hook_common as common
import pytest
import record_verdict as rv

pytestmark = pytest.mark.usefixtures("fake_checklist")

OK_LINES = (
    "Checklist:\nGOV-1: N/A — diff não altera arquitetura\nGIT-1: OK — nenhum arquivo sensível\n"
)
FAILED_LINES = (
    "Checklist:\nGOV-1: FALHA — sem ADR para nova lib\nGIT-1: OK — sem arquivos sensíveis\n"
)


def _report(verdict="APROVADO", checklist_lines=OK_LINES, problems="nenhum"):
    head = f"VEREDITO: {verdict}\nEscopo: a.py\nGates: tudo ✅\n"
    return f"{head}{checklist_lines}Problemas: {problems}\n"


def _run(state, monkeypatch, message, **extra):
    """Roda o hook do code-reviewer e devolve o veredito salvo (`None` se nada foi salvo)."""
    data = {"agent_type": "code-reviewer", "last_assistant_message": message, **extra}
    monkeypatch.setattr(common, "read_input", lambda: data)
    rv.main()
    saved = state / "state" / "verdicts.json"
    return json.loads(saved.read_text())["code-reviewer"] if saved.exists() else None


@pytest.mark.parametrize(
    ("checklist_lines", "culprit"),
    [
        ("Checklist:\nGOV-1: N/A — diff não altera arquitetura\n", "GIT-1"),
        ("Checklist:\nGOV-1: OK\nGIT-1: OK — sem arquivos\n", "GOV-1"),
    ],
    ids=["missing-item", "no-evidence"],
)
def test_parse_report_rejects_incomplete_checklist(checklist_lines, culprit):
    message = _report(checklist_lines=checklist_lines)

    verdict, reason = rv.parse_report("code-reviewer", message)

    assert verdict is None
    assert culprit in reason


@pytest.mark.parametrize(
    "report",
    [
        _report(checklist_lines=FAILED_LINES),
        _report(problems="\n[IMPORTANTE] a.py:3 — falta teste"),
        _report(problems="[BLOQUEANTE] a.py:1 — segredo"),
        _report(problems="\n1. [BLOQUEANTE] a.py:1 — segredo"),
        _report(problems="\n**[BLOQUEANTE]** a.py:1 — segredo"),
        _report(problems="\n+ [importante] a.py:1 — falta teste"),
    ],
    ids=["failed-item", "dash", "inline", "numbered", "bold", "plus-lowercase"],
)
def test_parse_report_rejects_contradictory_approval(report):
    verdict, reason = rv.parse_report("code-reviewer", report)

    assert verdict is None
    assert reason.startswith(rv.CONTRADICTION)


def test_parse_report_accepts_rejection_with_failed_item():
    message = _report("REPROVADO", FAILED_LINES, "\n[BLOQUEANTE] a.py:1 — sem ADR")

    assert rv.parse_report("code-reviewer", message) == ("REPROVADO", "")


def test_record_verdict_blocks_contradiction_on_first_try(state, monkeypatch, capsys):
    message = _report(problems="\n[BLOQUEANTE] a.py:3 — segredo no código")

    saved = _run(state, monkeypatch, message)

    assert saved is None
    assert '"decision": "block"' in capsys.readouterr().out


def test_record_verdict_forces_rejection_when_contradiction_persists(state, monkeypatch):
    message = _report(problems="\n[BLOQUEANTE] a.py:3 — segredo no código")

    saved = _run(state, monkeypatch, message, stop_hook_active=True)

    assert saved["verdict"] == "REPROVADO"


def test_record_verdict_does_not_trust_a_clean_retry_after_a_contradiction(state, monkeypatch):
    bad = _report(checklist_lines=FAILED_LINES)
    _run(state, monkeypatch, bad, agent_id="a1")

    saved = _run(state, monkeypatch, _report(), agent_id="a1", stop_hook_active=True)

    assert saved["verdict"] == "REPROVADO"


def _marks(state):
    path = state / "state" / "contradictions.json"
    return json.loads(path.read_text()) if path.exists() else {}


def test_contradiction_mark_does_not_leak_to_another_agent_run(state, monkeypatch):
    _run(state, monkeypatch, _report(checklist_lines=FAILED_LINES), agent_id="a1")

    saved = _run(state, monkeypatch, _report(), agent_id="a2", stop_hook_active=True)

    assert saved["verdict"] == "APROVADO"


def test_contradiction_mark_is_consumed_by_the_retry(state, monkeypatch):
    _run(state, monkeypatch, _report(checklist_lines=FAILED_LINES), agent_id="a1")
    assert "a1" in _marks(state)

    _run(state, monkeypatch, _report(), agent_id="a1", stop_hook_active=True)

    assert "a1" not in _marks(state)


def test_contradiction_mark_only_applies_on_the_retry(state, monkeypatch):
    _run(state, monkeypatch, _report(checklist_lines=FAILED_LINES), agent_id="a1")

    saved = _run(state, monkeypatch, _report(), agent_id="a1")

    assert saved["verdict"] == "APROVADO"


def test_contradiction_marks_file_is_capped(state, monkeypatch):
    for index in range(rv.MAX_MARKS + 1):
        _run(state, monkeypatch, _report(checklist_lines=FAILED_LINES), agent_id=f"a{index}")

    marks = _marks(state)
    assert len(marks) == rv.MAX_MARKS
    assert "a0" not in marks


def test_parse_report_refuses_oversized_report():
    message = _report(problems="x" * rv.MAX_REPORT_CHARS)

    verdict, reason = rv.parse_report("code-reviewer", message)

    assert verdict is None
    assert "grande demais" in reason


def test_record_verdict_saves_checklist_counts(state, monkeypatch):
    saved = _run(state, monkeypatch, _report())

    assert saved["checklist"] == {"OK": 1, "N/A": 1, "FALHA": 0}
