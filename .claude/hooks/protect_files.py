"""Hook PreToolUse (Read/Edit/Write): proteção de segredos e das configs de qualidade.

- Nega leitura e escrita de `.env` e segredos (chaves, certificados).
- Nega edição manual de lockfiles e de `.claude/state` / `.claude/reports` (só os hooks gravam).
- Pede confirmação antes de alterar as configurações de qualidade, o gate, os hooks e a pasta
  `.claude/` (exceto `skills/` de terceiros), para o agente não afrouxar os gates para passar.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

import hook_common as common

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SECRET_NAME_RE = re.compile(r"^\.env(\..+)?$")
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore", ".jks"}
SECRET_GLOBS = ("id_rsa*", "id_ed25519*", "*service-account*.json", "*credentials*.json")
LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
}
STATE_DIRS = (".claude/state/", ".claude/reports/")
ASK_EXACT = {
    "frontend/package.json",
    ".gitignore",
    "frontend/.prettierignore",
    ".semgrepignore",
    ".mypy-baseline.json",
    "backend/pyproject.toml",
    ".pre-commit-config.yaml",
    ".jscpd.json",
    ".coverage-baseline.json",
    ".mcp.json",
    "CLAUDE.md",
    "Makefile",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/playwright.config.ts",
    ".claude/settings.json",
    ".claude/settings.local.json",
    "docs/checklist-engenharia.md",
}
# Mesmo conjunto que o fingerprint considera "código" (hook_common) mais o que só pede confirmação.
ASK_PREFIXES = (
    ".claude/skills/prepare-pr/",
    ".claude/skills/security-check/",
    ".claude/skills/clean-code/",
    ".claude/hooks/",
    *common.CODE_PREFIXES,
)
ASK_GLOBS = ("scripts/quality_gate.py", "scripts/gate_*.py", "scripts/check_*.py")


def relative(path_text: str) -> str:
    """Caminho relativo à raiz do projeto (ou absoluto, se estiver fora dele)."""
    path = Path(path_text)
    if not path.is_absolute():
        path = common.PROJECT_DIR / path
    resolved = path.resolve()
    try:
        return resolved.relative_to(common.PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def is_secret(rel: str) -> bool:
    """`.env` (exceto `.env.example`), chaves e certificados."""
    name = Path(rel).name
    if name == ".env.example":
        return False
    if SECRET_NAME_RE.match(name) or Path(name).suffix in SECRET_SUFFIXES:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_GLOBS)


def decide(tool: str, rel: str) -> tuple[str, str] | None:
    """Decide sobre o acesso de `tool` a `rel`: `("deny"|"ask", motivo)` ou `None`."""
    if is_secret(rel):
        return "deny", f"{rel} contém segredos: acesso bloqueado (use .env.example)."
    if tool not in WRITE_TOOLS:
        return None
    if rel.startswith(STATE_DIRS):
        return "deny", "Só os hooks gravam em .claude/state e .claude/reports."
    if Path(rel).name in LOCKFILES:
        return "deny", f"{Path(rel).name} é gerado pelo gerenciador de pacotes; não edite à mão."
    guarded = (
        rel in ASK_EXACT
        or rel.startswith(ASK_PREFIXES)
        or any(fnmatch.fnmatch(rel, pattern) for pattern in ASK_GLOBS)
    )
    if guarded:
        return "ask", f"{rel} define gates/processo: confirme a alteração (não afrouxe os gates)."
    return None


def target_paths(data: dict[str, object]) -> list[str]:
    """Caminhos alvo da chamada de ferramenta."""
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    keys = ("file_path", "notebook_path", "path")
    return [str(tool_input[k]) for k in keys if tool_input.get(k)]


def main() -> int:
    """Lê a chamada de ferramenta do stdin e responde allow/ask/deny."""
    data = common.read_input()
    tool = str(data.get("tool_name", ""))
    for raw in target_paths(data):
        outcome = decide(tool, relative(raw))
        if outcome:
            common.emit(common.pretool_decision(*outcome))
            break
    return 0


if __name__ == "__main__":
    sys.exit(
        common.run_safely(
            main,
            "protect_files",
            common.pretool_decision("ask", "Hook protect_files falhou: confirme manualmente."),
        )
    )
