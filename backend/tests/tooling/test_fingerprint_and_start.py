import json

import hook_common as common
import pytest
import record_verdict as rv
import subagent_start as sas


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "STATE_DIR", tmp_path)
    monkeypatch.setattr(common, "STARTS_FILE", tmp_path / "starts.json")
    monkeypatch.setattr(common, "PROJECT_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "rel",
    [
        "backend/app/main.py",
        "frontend/src/App.tsx",
        ".github/workflows/ci.yml",
        ".coverage-baseline.json",
        ".jscpd.json",
        ".gitignore",
        "frontend/tsconfig.json",
        ".claude/settings.json",
        "docs/checklist-engenharia.md",
        ".claude/agents/qa-tester.md",
        ".claude/rules/reliability-data.md",
        ".claude/skills/checklist/SKILL.md",
        ".claude/skills/adr/SKILL.md",
        ".claude/skills/threat-model/SKILL.md",
    ],
)
def test_is_code_file_covers_code_and_gate_configs(rel):
    assert common.is_code_file(rel)


@pytest.mark.parametrize("rel", ["README.md", "docs/design-system.md", "frontend/dist/x.js"])
def test_is_code_file_ignores_documentation_and_build_output(rel):
    assert not common.is_code_file(rel)


def _git_answers(monkeypatch, changed, deleted):
    def fake_git(*args):
        if "--diff-filter=D" in args:
            return "\n".join(deleted)
        if "--diff-filter=ACMR" in args:
            return "\n".join(changed)
        return ""

    monkeypatch.setattr(common, "git", fake_git)
    monkeypatch.setattr(common, "base_ref", lambda: "origin/main")


def test_changed_code_files_include_deleted_files_as_markers(monkeypatch):
    _git_answers(monkeypatch, ["backend/app/a.py"], ["backend/tests/test_security.py", "README.md"])

    assert common.changed_code_files() == [
        "backend/app/a.py",
        "deleted:backend/tests/test_security.py",
    ]


def test_fingerprint_changes_when_a_tracked_test_is_deleted(state, monkeypatch):
    (state / "backend" / "app").mkdir(parents=True)
    (state / "backend" / "app" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git_answers(monkeypatch, ["backend/app/a.py"], [])
    before, _ = common.fingerprint()

    _git_answers(monkeypatch, ["backend/app/a.py"], ["backend/tests/test_security.py"])
    after, _ = common.fingerprint()

    assert before != after


def test_subagent_start_stamps_fingerprint_by_agent_id(state, monkeypatch):
    monkeypatch.setattr(common, "fingerprint", lambda: ("fp-start", []))
    monkeypatch.setattr(
        common, "read_input", lambda: {"agent_type": "code-reviewer", "agent_id": "a1"}
    )

    sas.main()

    stamped = json.loads((state / "starts.json").read_text(encoding="utf-8"))
    assert stamped["a1"]["fingerprint"] == "fp-start"


def test_subagent_start_ignores_other_agents(state, monkeypatch):
    monkeypatch.setattr(common, "fingerprint", lambda: ("fp", []))
    monkeypatch.setattr(common, "read_input", lambda: {"agent_type": "Explore", "agent_id": "a2"})

    sas.main()

    assert not (state / "starts.json").exists()


def test_reconcile_keeps_verdict_when_code_did_not_change(state):
    common.write_json(common.STARTS_FILE, {"a1": {"fingerprint": "fp1"}})

    assert rv.reconcile_with_start("a1", "APROVADO", "fp1") == ("APROVADO", "fp1")


def test_reconcile_invalidates_verdict_when_code_changed_during_review(state):
    common.write_json(common.STARTS_FILE, {"a1": {"fingerprint": "fp-start"}})

    verdict, stamped = rv.reconcile_with_start("a1", "APROVADO", "fp-now")

    assert verdict is None
    assert stamped == "fp-start"


def test_reconcile_without_start_record_uses_current_fingerprint(state):
    assert rv.reconcile_with_start("desconhecido", "APROVADO", "fp-now") == ("APROVADO", "fp-now")


def _verdict_line(monkeypatch, tmp_path, **info):
    import session_start as ss

    state = {"code-reviewer": {"verdict": "APROVADO", "at": "t", "fingerprint": "fp", **info}}
    monkeypatch.setattr(common, "STATE_DIR", tmp_path)
    common.write_json(tmp_path / "verdicts.json", state)
    return ss.verdict_lines("fp")[0]


def test_session_start_verdict_lines_show_checklist_counts(monkeypatch, tmp_path):
    counts = {"OK": 40, "N/A": 9, "FALHA": 0}

    line = _verdict_line(monkeypatch, tmp_path, checklist=counts)

    assert "checklist OK 40 · N/A 9 · FALHA 0" in line


def test_session_start_verdict_lines_accept_legacy_state_without_checklist(monkeypatch, tmp_path):
    line = _verdict_line(monkeypatch, tmp_path)

    assert line == "- code-reviewer: APROVADO em t (vale para o código atual)"
