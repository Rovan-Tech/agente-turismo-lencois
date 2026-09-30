import hook_common as common
import protect_files as pf
import pytest


def _kind(tool: str, rel: str) -> str | None:
    outcome = pf.decide(tool, rel)
    return outcome[0] if outcome else None


@pytest.mark.parametrize(
    ("tool", "rel"),
    [
        ("Read", ".env"),
        ("Read", "backend/.env.production"),
        ("Edit", "backend/.env"),
        ("Read", "certs/server.pem"),
        ("Write", "keys/id_rsa"),
        ("Edit", "frontend/package-lock.json"),
        ("Write", ".claude/state/verdicts.json"),
        ("Edit", ".claude/reports/x.md"),
    ],
)
def test_decide_denies_secrets_lockfiles_and_state(tool, rel):
    assert _kind(tool, rel) == "deny"


@pytest.mark.parametrize(
    "rel",
    [
        "backend/pyproject.toml",
        ".github/workflows/ci.yml",
        ".pre-commit-config.yaml",
        ".claude/settings.json",
        ".claude/hooks/guard_bash.py",
        ".claude/agents/code-reviewer.md",
        "scripts/quality_gate.py",
        ".coverage-baseline.json",
        "docs/checklist-engenharia.md",
        ".claude/rules/ai-governance.md",
        ".claude/skills/checklist/SKILL.md",
        ".claude/skills/adr/SKILL.md",
        ".claude/skills/threat-model/SKILL.md",
    ],
)
def test_decide_asks_before_editing_quality_configs(rel):
    assert _kind("Edit", rel) == "ask"


@pytest.mark.parametrize(
    ("tool", "rel"),
    [
        ("Read", "backend/.env.example"),
        ("Read", ".claude/state/verdicts.json"),
        ("Read", "backend/pyproject.toml"),
        ("Edit", "backend/app/main.py"),
        ("Edit", ".claude/skills/engineering/whatever/SKILL.md"),
        ("Write", "frontend/src/App.tsx"),
    ],
)
def test_decide_allows_regular_access(tool, rel):
    assert pf.decide(tool, rel) is None


def test_relative_resolves_project_paths_and_keeps_outside_absolute():
    inside = str(common.PROJECT_DIR / "backend" / "app" / "main.py")

    assert pf.relative(inside) == "backend/app/main.py"
    assert pf.relative("/etc/passwd") == "/etc/passwd"


def test_main_emits_deny_for_env_read(monkeypatch, capsys):
    data = {"tool_name": "Read", "tool_input": {"file_path": "backend/.env"}}
    monkeypatch.setattr(common, "read_input", lambda: data)

    assert pf.main() == 0
    assert '"permissionDecision": "deny"' in capsys.readouterr().out
