"""Utilitários compartilhados pelo gate de qualidade: git, execução de comandos e diff por linha."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
TOOL_DIRS = ("scripts", ".claude/hooks")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
COMMAND_NOT_FOUND = 127
TIMEOUT_EXIT = 124

LineSet = frozenset[int] | None
"""Linhas alteradas de um arquivo; `None` significa arquivo novo (todas as linhas)."""


@dataclass(frozen=True)
class RunResult:
    """Resultado de um comando externo."""

    returncode: int
    output: str


def venv_python() -> str:
    """Retorna o Python do venv do backend, ou o interpretador atual se ele não existir."""
    for candidate in (
        BACKEND / ".venv" / "bin" / "python",
        BACKEND / ".venv" / "Scripts" / "python.exe",
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run(cmd: Sequence[str], cwd: Path = ROOT, timeout: int = 900) -> RunResult:
    """Executa um comando e devolve código de saída e saída combinada.

    Args:
        cmd: Comando e argumentos (sem shell).
        cwd: Diretório de execução.
        timeout: Limite em segundos.

    Returns:
        O resultado; erros de execução viram código 127 (não encontrado) ou 124 (timeout).
    """
    try:
        proc = subprocess.run(  # noqa: S603  # comando montado pelo gate, sem entrada externa
            list(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return RunResult(COMMAND_NOT_FOUND, f"comando não encontrado: {cmd[0]}")
    except subprocess.TimeoutExpired:
        return RunResult(TIMEOUT_EXIT, f"timeout de {timeout}s: {' '.join(cmd)}")
    return RunResult(proc.returncode, (proc.stdout + proc.stderr).strip())


def base_ref() -> str:
    """Branch base para comparar o diff (`origin/main`, senão `main`)."""
    for ref in ("origin/main", "main"):
        if run(["git", "rev-parse", "--verify", "--quiet", ref]).returncode == 0:
            return ref
    return "HEAD"


def merge_base(ref: str) -> str:
    """Ancestral comum entre `HEAD` e `ref`."""
    result = run(["git", "merge-base", "HEAD", ref])
    return result.output.splitlines()[0] if result.returncode == 0 and result.output else "HEAD"


def parse_diff(diff: str) -> dict[Path, LineSet]:
    """Converte a saída de `git diff -U0` em linhas alteradas por arquivo."""
    changed: dict[Path, set[int]] = {}
    current: Path | None = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = (ROOT / line[6:]).resolve() if line.startswith("+++ b/") else None
            if current is not None:
                changed.setdefault(current, set())
        elif current is not None:
            changed[current].update(_hunk_lines(line))
    return {path: frozenset(lines) for path, lines in changed.items()}


def _hunk_lines(line: str) -> range:
    """Linhas novas descritas por um cabeçalho `@@`; vazio para qualquer outra linha."""
    match = HUNK_RE.match(line)
    if not match:
        return range(0)
    start, count = int(match.group(1)), int(match.group(2) or 1)
    return range(start, start + count)


def changed_lines(base: str) -> dict[Path, LineSet]:
    """Linhas alteradas desde o ancestral comum com `base`, incluindo o que ainda não foi commitado.

    Arquivos não rastreados entram com `None` (todas as linhas). Arquivos apagados são ignorados.
    """
    diff = run(["git", "diff", "-U0", "--no-color", "--diff-filter=ACMR", merge_base(base)])
    result = parse_diff(diff.output)
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    merged: dict[Path, LineSet] = dict(result)
    for name in untracked.output.splitlines():
        path = (ROOT / name).resolve()
        if path.is_file():
            merged[path] = None
    return {path: lines for path, lines in merged.items() if path.exists()}


def touches(lines: LineSet, start: int, end: int | None = None) -> bool:
    """Indica se o intervalo `[start, end]` contém alguma linha alterada."""
    if lines is None:
        return True
    return any(start <= line <= (end if end is not None else start) for line in lines)


def is_python_source(path: Path) -> bool:
    """Arquivo `.py` que o gate deve verificar (código do backend, scripts e hooks)."""
    if path.suffix != ".py":
        return False
    parts = path.relative_to(ROOT).parts
    return parts[0] in {"backend", "scripts"} or parts[:2] == (".claude", "hooks")


def is_frontend_source(path: Path) -> bool:
    """Arquivo de interface do frontend (código, estilos e HTML)."""
    rel = path.relative_to(ROOT).parts
    return rel[0] == "frontend" and path.suffix in {".ts", ".tsx", ".css", ".html", ".js"}
