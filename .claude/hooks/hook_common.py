"""Utilitários compartilhados pelos hooks do Claude Code (somente biblioteca padrão).

Contém a leitura do JSON de entrada, as respostas no formato atual dos hooks, o estado em
`.claude/state/` e o "fingerprint do código" usado pelo portão final (hook Stop).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE_DIR = PROJECT_DIR / ".claude" / "state"
REPORTS_DIR = PROJECT_DIR / ".claude" / "reports"
STARTS_FILE = STATE_DIR / "starts.json"
REVIEW_AGENTS = ("code-reviewer", "qa-tester")

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".css", ".html"}
CODE_ROOTS = ("backend/", "frontend/src/", "frontend/tests/", "scripts/", ".claude/hooks/")
CODE_PREFIXES = (
    ".github/workflows/",
    ".claude/agents/",
    ".claude/rules/",
    ".claude/skills/feature/",
    ".claude/skills/bugfix/",
    ".claude/skills/revisar/",
    ".claude/skills/qa/",
    ".claude/skills/gate/",
    ".claude/skills/checklist/",
    ".claude/skills/adr/",
    ".claude/skills/threat-model/",
)
CODE_FILES = {
    "docs/checklist-engenharia.md",
    ".coverage-baseline.json",
    ".mypy-baseline.json",
    ".jscpd.json",
    ".pre-commit-config.yaml",
    ".gitignore",
    ".mcp.json",
    ".claude/settings.json",
    "Makefile",
    "frontend/tsconfig.json",
    "frontend/.prettierignore",
    "backend/pyproject.toml",
    "backend/requirements.txt",
    "backend/requirements-dev.txt",
    "backend/Dockerfile",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/tailwind.config.js",
    "frontend/vite.config.ts",
    "frontend/playwright.config.ts",
}
GIT_TIMEOUT = 20
DELETED_PREFIX = "deleted:"


def git(*args: str) -> str:
    """Executa um comando git na raiz do projeto e devolve a saída (vazia em caso de erro)."""
    try:
        proc = subprocess.run(  # noqa: S603  # argumentos fixos definidos pelos hooks
            ["git", *args],  # noqa: S607  # git vem do PATH do desenvolvedor
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def current_branch() -> str:
    """Nome da branch atual (vazio se não for possível descobrir)."""
    return git("rev-parse", "--abbrev-ref", "HEAD")


def base_ref() -> str:
    """Branch base do diff: `origin/main`, senão `main`."""
    for ref in ("origin/main", "main"):
        if git("rev-parse", "--verify", "--quiet", ref):
            return ref
    return "HEAD"


def is_code_file(rel: str) -> bool:
    """Indica se um caminho relativo conta como "código" para o fingerprint."""
    if rel in CODE_FILES or rel.startswith(CODE_PREFIXES):
        return True
    return rel.startswith(CODE_ROOTS) and Path(rel).suffix in CODE_SUFFIXES


def changed_code_files() -> list[str]:
    """Arquivos de código alterados desde a base, os novos (incluindo não rastreados) e os apagados.

    Os apagados entram como `deleted:<caminho>`: remover um teste também muda o fingerprint.
    """
    base = git("merge-base", "HEAD", base_ref()) or "HEAD"
    tracked = git("diff", "--name-only", "--diff-filter=ACMR", base).splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    removed = git("diff", "--name-only", "--diff-filter=D", base).splitlines()
    present = {p for p in (*tracked, *untracked) if is_code_file(p)}
    return sorted(present | {f"{DELETED_PREFIX}{p}" for p in removed if is_code_file(p)})


def fingerprint() -> tuple[str, list[str]]:
    """Hash do conteúdo dos arquivos de código alterados e novos.

    Returns:
        O digest e a lista de arquivos considerados. Arquivos ignorados pelo git ficam de fora.
    """
    files = changed_code_files()
    digest = hashlib.sha256()
    for rel in files:
        if rel.startswith(DELETED_PREFIX):
            digest.update(rel.encode())
            continue
        path = PROJECT_DIR / rel
        if not path.is_file():
            continue
        digest.update(rel.encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest(), files


def read_json(path: Path, default: Any) -> Any:  # noqa: ANN401  # o formato varia por arquivo
    """Lê um JSON do disco, devolvendo `default` se não existir ou estiver corrompido."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:  # noqa: ANN401  # serializa qualquer estrutura JSON
    """Grava um JSON de forma atômica (arquivo temporário + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    Path(tmp).replace(path)


def read_input() -> dict[str, Any]:
    """Lê o JSON que o Claude Code envia pelo stdin; vazio se ausente ou inválido."""
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def emit(payload: dict[str, Any]) -> None:
    """Escreve a resposta JSON do hook no stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def pretool_decision(decision: str, reason: str) -> dict[str, Any]:
    """Monta a resposta de um hook PreToolUse (`allow`, `deny` ou `ask`)."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def fail_message(payload: dict[str, Any], reason: str) -> None:
    """Bloqueia a parada (Stop/SubagentStop) devolvendo o motivo ao Claude."""
    emit({**payload, "decision": "block", "reason": reason})


def run_safely(main: Callable[[], int], name: str, fallback: dict[str, Any] | None = None) -> int:
    """Executa o hook sem nunca travar a sessão: exceções viram um aviso e saída 0.

    Args:
        main: Função principal do hook.
        name: Nome do hook, para a mensagem de aviso.
        fallback: Resposta a emitir se o hook falhar (os guardas usam `ask`, para não liberar
            às cegas nem bloquear a sessão); sem ela, só o aviso é emitido.
    """
    try:
        return main()
    except Exception as exc:  # um hook com defeito não pode derrubar a sessão
        sys.stderr.write(f"[hook {name}] erro interno ignorado: {type(exc).__name__}: {exc}\n")
        emit(fallback or {"systemMessage": f"Hook {name} falhou ({type(exc).__name__}); sem ele."})
        return 0
