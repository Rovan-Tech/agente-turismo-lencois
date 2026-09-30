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


HANDBACK = "SubagentHandback"


def _handback(message):
    return {"type": "tool_use", "name": HANDBACK, "input": {"message": message}}


def _record(state, monkeypatch, transcript_lines=None, **extra):
    """Roda o hook do code-reviewer; devolve o veredito salvo. `transcript_lines` vira o JSONL."""
    data = {"agent_type": "code-reviewer", **extra}
    if transcript_lines is not None:
        path = state / "agent-x.jsonl"
        raw = transcript_lines if isinstance(transcript_lines, bytes) else transcript_lines.encode()
        path.write_bytes(raw)
        data["agent_transcript_path"] = str(path)
    _hook_input(monkeypatch, rv, data)
    rv.main()
    saved = json.loads((state / "state" / "verdicts.json").read_text())
    return saved["code-reviewer"]["verdict"]


def _transcript(*turns):
    return "\n".join(json.dumps({"message": {"content": blocks}}) for blocks in turns) + "\n"


def test_record_verdict_reads_report_from_subagent_handback(state, monkeypatch):
    lines = _transcript([_handback(REVIEWER_OK)])

    verdict = _record(state, monkeypatch, lines, last_assistant_message="Entreguei o relatório.")

    assert verdict == "APROVADO"
    report = next((state / "reports").glob("*-code-reviewer.md"))
    assert report.read_text(encoding="utf-8") == REVIEWER_OK


def test_record_verdict_uses_last_handback_of_the_transcript(state, monkeypatch):
    lines = _transcript(
        [_handback(QA_OK)], [{"type": "text", "text": "ok"}, _handback(REVIEWER_OK)]
    )

    assert _record(state, monkeypatch, lines) == "APROVADO"


def test_record_verdict_ignores_session_transcript_path(state, monkeypatch):
    """`transcript_path` é o da sessão principal; só o do próprio subagent vale."""
    session = state / "session.jsonl"
    session.write_text(_transcript([_handback(REVIEWER_OK)]), encoding="utf-8")

    verdict = _record(
        state,
        monkeypatch,
        last_assistant_message="feito",
        transcript_path=str(session),
        stop_hook_active=True,
    )

    assert verdict == "INVALIDO"


def _bad_handback(**block):
    """Linha de transcript com um bloco SubagentHandback de estrutura inválida."""
    return _transcript([{"type": "tool_use", "name": HANDBACK, **block}])


MALFORMED_TRANSCRIPTS = {
    "empty": "",
    "broken-json": "{quebrado",
    "no-handback": '{"type": "assistant"}',
    "invalid-utf8": b"\xff\xfe\x00{\n",
    "deeply-nested": "[" * 100_000,
    "line-not-object": "[1]\n5\nnull\n",
    "message-not-dict": '{"message": "x"}',
    "content-not-list": _transcript("texto"),
    "input-is-string": _bad_handback(input="x"),
    "input-is-null": _bad_handback(input=None),
    "input-is-list": _bad_handback(input=["x"]),
    "message-not-string": _bad_handback(input={"message": 5}),
}


@pytest.mark.parametrize("content", MALFORMED_TRANSCRIPTS.values(), ids=MALFORMED_TRANSCRIPTS)
def test_record_verdict_falls_back_when_transcript_is_unusable(state, monkeypatch, content):
    verdict = _record(state, monkeypatch, content, last_assistant_message=REVIEWER_OK)

    assert verdict == "APROVADO"


@pytest.mark.parametrize(
    "name",
    ["agent-x.txt", "agent-x.jsonl\x00", "a" * 5000 + ".jsonl"],
    ids=["suffix", "nul-byte", "name-too-long"],
)
def test_record_verdict_ignores_unsafe_transcript_paths(state, monkeypatch, name):
    """Um handback existe em `agent-x.txt`, mas o caminho inseguro faz o hook usar o fallback."""
    (state / "agent-x.txt").write_text(_transcript([_handback(REVIEWER_OK)]), encoding="utf-8")
    fallback = REVIEWER_OK.replace("Escopo: a.py", "Escopo: fallback.py")

    verdict = _record(
        state,
        monkeypatch,
        last_assistant_message=fallback,
        agent_transcript_path=str(state / name),
    )

    assert verdict == "APROVADO"
    report = next((state / "reports").glob("*-code-reviewer.md"))
    assert report.read_text(encoding="utf-8") == fallback


def test_record_verdict_falls_back_when_transcript_is_missing(state, monkeypatch):
    missing = str(state / "nao-existe.jsonl")

    verdict = _record(
        state, monkeypatch, last_assistant_message=REVIEWER_OK, agent_transcript_path=missing
    )

    assert verdict == "APROVADO"


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
