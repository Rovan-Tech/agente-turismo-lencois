"""Hook PostToolUse (Edit/Write): qualidade na hora.

Formata e corrige o arquivo editado, roda o gate rápido restrito a ele e procura gambiarras nas
linhas adicionadas (silenciadores sem código, skip/xfail, print, except: pass, segredos). Devolve os
problemas ao Claude (exit 2 + stderr) para ele corrigir antes de seguir.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import hook_common as common

PY_ROOTS = ("backend/", "scripts/", ".claude/hooks/")
FRONTEND_SUFFIXES = {".ts", ".tsx", ".css", ".html", ".js"}
TIMEOUT = 80
MAX_REPORTED = 20
SKIP_SCAN_PREFIXES = (".claude/hooks/", "backend/tests/tooling/")

ANTI_PATTERNS: tuple[tuple[re.Pattern[str], str, frozenset[str]], ...] = (
    (
        re.compile(r"#\s*type:\s*ignore(?!\[)"),
        "`# type: ignore` sem código de erro",
        frozenset({".py"}),
    ),
    (
        re.compile(r"#\s*noqa(?!:\s*[A-Z]+\d+)"),
        "`# noqa` sem código da regra",
        frozenset({".py"}),
    ),
    (
        re.compile(r"@ts-ignore|eslint-disable(?!-next-line\s+\S)"),
        "silenciador de tipos/lint no TypeScript",
        frozenset({".ts", ".tsx", ".js"}),
    ),
    (
        re.compile(r"pytest\.mark\.(skip|xfail|skipif)|@unittest\.skip"),
        "teste pulado/xfail",
        frozenset({".py"}),
    ),
    (
        re.compile(r"\b(it|test|describe)\.(skip|only|fixme)\b|\b(xit|xdescribe|fit|fdescribe)\("),
        "teste pulado/focado",
        frozenset({".ts", ".tsx", ".js"}),
    ),
    (re.compile(r"(?<![\w.])print\("), "`print(` (use logging)", frozenset({".py"})),
    (re.compile(r"\bconsole\.log\("), "`console.log(` no painel", frozenset({".ts", ".tsx"})),
    (re.compile(r"except\s*:\s*(pass)?\s*$"), "`except:` nu", frozenset({".py"})),
    (
        re.compile(r"except\s+\w[\w.]*(\s+as\s+\w+)?\s*:\s*pass\b"),
        "exceção engolida (`except ...: pass`)",
        frozenset({".py"}),
    ),
    (re.compile(r"\bbreakpoint\(\)|\bpdb\.set_trace"), "breakpoint esquecido", frozenset({".py"})),
    (re.compile(r"^\s*debugger;?\s*$"), "`debugger` esquecido", frozenset({".ts", ".tsx", ".js"})),
    (
        re.compile(
            r"(api[_-]?key|secret|token|passw(or)?d)\w*\s*[:=]\s*[\"'][A-Za-z0-9_\-/+=]{20,}[\"']"
            r"|gsk_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|EAA[A-Za-z0-9]{50,}"
            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----",
            re.I,
        ),
        "string com cara de segredo",
        frozenset({".py", ".ts", ".tsx", ".js", ".html"}),
    ),
)


def added_lines(rel: str) -> list[tuple[int, str]]:
    """Linhas adicionadas ao arquivo desde a base (todas, se for arquivo novo)."""
    path = common.PROJECT_DIR / rel
    if not path.is_file():
        return []
    base = common.git("merge-base", "HEAD", common.base_ref()) or "HEAD"
    diff = common.git("diff", "-U0", "--no-color", base, "--", rel)
    tracked = bool(common.git("ls-files", "--error-unmatch", "--", rel))
    if not diff and tracked:
        return []
    if not diff:
        text = path.read_text(encoding="utf-8", errors="replace")
        return list(enumerate(text.splitlines(), start=1))
    found: list[tuple[int, str]] = []
    line_no = 0
    for raw in diff.splitlines():
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", raw)
        if hunk:
            line_no = int(hunk.group(1))
        elif raw.startswith("+") and not raw.startswith("+++"):
            found.append((line_no, raw[1:]))
            line_no += 1
    return found


def scan_anti_patterns(rel: str, lines: list[tuple[int, str]]) -> list[str]:
    """Aplica o detector anti-gambiarra às linhas adicionadas de `rel`."""
    if rel.startswith(SKIP_SCAN_PREFIXES):
        return []
    suffix = Path(rel).suffix
    problems = []
    for number, text in lines:
        for pattern, label, suffixes in ANTI_PATTERNS:
            if suffix in suffixes and pattern.search(text):
                problems.append(f"{rel}:{number} {label}")
    return problems


def _venv_python() -> str:
    for candidate in ("bin/python", "Scripts/python.exe"):
        path = common.PROJECT_DIR / "backend" / ".venv" / candidate
        if path.exists():
            return str(path)
    return sys.executable


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603  # comandos montados por este hook
            cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 0, f"(não foi possível rodar {cmd[0]}: {exc})"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def autofix(rel: str) -> None:
    """Formata e aplica correções seguras no arquivo editado."""
    path = str(common.PROJECT_DIR / rel)
    if rel.startswith(PY_ROOTS):
        config = str(common.PROJECT_DIR / "backend" / "pyproject.toml")
        ruff = [_venv_python(), "-m", "ruff"]
        backend = common.PROJECT_DIR / "backend"
        _run([*ruff, "check", "--fix-only", "--quiet", "--config", config, path], backend)
        _run([*ruff, "format", "--quiet", "--config", config, path], backend)
    elif Path(rel).suffix in FRONTEND_SUFFIXES and rel.startswith("frontend/"):
        npx = shutil.which("npx")
        if npx and (common.PROJECT_DIR / "frontend" / "node_modules").exists():
            _run(
                [npx, "prettier", "--write", "--log-level", "silent", path],
                common.PROJECT_DIR / "frontend",
            )


def gate_problems(rel: str) -> list[str]:
    """Roda o gate rápido restrito ao arquivo e devolve as linhas de falha."""
    is_py = rel.startswith(PY_ROOTS) and rel.endswith(".py")
    is_fe = rel.startswith("frontend/") and Path(rel).suffix in FRONTEND_SUFFIXES
    if not (is_py or is_fe):
        return []
    gate = common.PROJECT_DIR / "scripts" / "quality_gate.py"
    if not gate.exists():
        return []
    code, out = _run([_venv_python(), str(gate), "--fast", "--files", rel], common.PROJECT_DIR)
    if code == 0:
        return []
    ignored = ("Gate", "✅")
    return [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith(ignored)]


def main() -> int:
    """Processa o arquivo editado e devolve os problemas ao Claude, se houver."""
    data = common.read_input()
    tool_input = data.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not raw:
        return 0
    path = Path(raw)
    path = path if path.is_absolute() else common.PROJECT_DIR / path
    try:
        rel = path.resolve().relative_to(common.PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return 0
    if not path.is_file() or not common.is_code_file(rel):
        return 0
    autofix(rel)
    problems = gate_problems(rel) + scan_anti_patterns(rel, added_lines(rel))
    if not problems:
        return 0
    shown = problems[:MAX_REPORTED]
    extra = f"\n… e mais {len(problems) - MAX_REPORTED}" if len(problems) > MAX_REPORTED else ""
    sys.stderr.write(f"Corrija antes de seguir ({rel}):\n" + "\n".join(shown) + extra + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "post_edit_quality"))
