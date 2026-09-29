import json

import hook_common as common
import pytest
import record_verdict as rv
import session_start as ss
import stop_gate as sg

REVIEWER_OK = (
    "VEREDITO: APROVADO\nEscopo: a.py\nGates: tudo ✅\nProblemas: nenhum\nPontos positivos: ok\n"
)
QA_OK = "VEREDITO: REPROVADO\nTestes: 1/1\nCritérios de aceite:\n[❌] x\nBugs: y\n"


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(common, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(rv, "VERDICTS_FILE", tmp_path / "state" / "verdicts.json")
    monkeypatch.setattr(common, "STARTS_FILE", tmp_path / "state" / "starts.json")
    monkeypatch.setattr(common, "fingerprint", lambda: ("fp2", ["backend/app/a.py"]))
    return tmp_path


def _hook_input(monkeypatch, module, data):
    monkeypatch.setattr(module.common, "read_input", lambda: data)


def test_parse_report_accepts_valid_report():
    assert rv.parse_report("code-reviewer", REVIEWER_OK) == ("APROVADO", "")


@pytest.mark.parametrize(
    "message",
    [
        "Tudo certo!",
        "Texto antes\nVEREDITO: APROVADO\nEscopo: x",
        "VEREDITO: TALVEZ\nEscopo: x",
        "VEREDITO: APROVADO\nEscopo: x",
    ],
)
def test_parse_report_rejects_malformed_reports(message):
    verdict, reason = rv.parse_report("code-reviewer", message)

    assert verdict is None
    assert reason


def test_record_verdict_saves_state_and_report(state, monkeypatch):
    data = {"agent_type": "code-reviewer", "last_assistant_message": REVIEWER_OK}
    _hook_input(monkeypatch, rv, data)

    assert rv.main() == 0

    saved = json.loads((state / "state" / "verdicts.json").read_text())
    assert saved["code-reviewer"]["verdict"] == "APROVADO"
    assert saved["code-reviewer"]["fingerprint"] == "fp2"
    assert len(list((state / "reports").glob("*-code-reviewer.md"))) == 1


def test_record_verdict_blocks_malformed_report_once(state, monkeypatch, capsys):
    data = {"agent_type": "qa-tester", "last_assistant_message": "feito"}
    _hook_input(monkeypatch, rv, data)

    rv.main()

    assert '"decision": "block"' in capsys.readouterr().out
    assert not (state / "state" / "verdicts.json").exists()


def test_record_verdict_marks_invalid_after_retry(state, monkeypatch):
    data = {"agent_type": "qa-tester", "last_assistant_message": "feito", "stop_hook_active": True}
    _hook_input(monkeypatch, rv, data)

    rv.main()

    saved = json.loads((state / "state" / "verdicts.json").read_text())
    assert saved["qa-tester"]["verdict"] == "INVALIDO"


def test_record_verdict_ignores_other_agents(state, monkeypatch):
    _hook_input(monkeypatch, rv, {"agent_type": "Explore", "last_assistant_message": "x"})

    rv.main()

    assert not (state / "state").exists()


def _start(fingerprint="fp1"):
    common.write_json(common.STATE_DIR / "session-s1.json", {"fingerprint": fingerprint})


def _approve(fingerprint, agents=common.REVIEW_AGENTS):
    verdicts = {a: {"verdict": "APROVADO", "fingerprint": fingerprint} for a in agents}
    common.write_json(common.STATE_DIR / "verdicts.json", verdicts)


@pytest.fixture
def stop_session(state, monkeypatch):
    """Sessão iniciada com o fingerprint antigo; o código atual (fp2) já mudou."""
    _start()
    _hook_input(monkeypatch, sg, {"session_id": "s1"})


@pytest.mark.parametrize(
    "make_ready",
    [lambda: _start("fp2"), lambda: _approve("fp2")],
    ids=["code-did-not-change", "both-approved-for-current-code"],
)
def test_stop_allows_when_nothing_is_pending(stop_session, capsys, make_ready):
    make_ready()

    assert sg.main() == 0
    assert capsys.readouterr().out == ""


def test_stop_blocks_when_code_changed_without_approvals(stop_session, capsys):
    sg.main()

    out = capsys.readouterr().out
    assert '"decision": "block"' in out
    assert "code-reviewer" in out
    assert "qa-tester" in out


def test_stop_blocks_when_approvals_are_stale(stop_session, capsys):
    _approve("fp-old")

    sg.main()

    assert '"decision": "block"' in capsys.readouterr().out


def test_stop_releases_after_three_blocks_without_progress(stop_session, capsys):
    for _ in range(sg.MAX_BLOCKS):
        sg.main()
    capsys.readouterr()
    sg.main()

    out = capsys.readouterr().out
    assert "systemMessage" in out
    assert "block" not in out


def test_stop_resets_counter_when_progress_happens(stop_session, capsys):
    for _ in range(sg.MAX_BLOCKS):
        sg.main()
    _approve("fp2", agents=["code-reviewer"])
    capsys.readouterr()

    sg.main()

    assert '"decision": "block"' in capsys.readouterr().out


def test_session_start_records_fingerprint_once_and_injects_context(state, monkeypatch, capsys):
    monkeypatch.setattr(common, "fingerprint", lambda: ("fpA", []))
    _hook_input(monkeypatch, ss, {"session_id": "s9"})

    ss.main()
    monkeypatch.setattr(common, "fingerprint", lambda: ("fpB", []))
    ss.main()

    saved = json.loads((state / "state" / "session-s9.json").read_text())
    assert saved["fingerprint"] == "fpA"
    assert "Fluxo obrigatório" in capsys.readouterr().out


def test_run_safely_swallows_internal_errors(capsys):
    def boom():
        raise RuntimeError("falha")

    assert common.run_safely(boom, "teste") == 0
    assert "Hook teste falhou" in capsys.readouterr().out


def test_run_safely_emits_fallback_decision_when_given(capsys):
    def boom():
        raise RuntimeError("falha")

    fallback = common.pretool_decision("ask", "confirme")

    assert common.run_safely(boom, "guarda", fallback) == 0
    assert '"permissionDecision": "ask"' in capsys.readouterr().out
