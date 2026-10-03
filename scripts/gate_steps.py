"""Etapas do gate que dependem do diff: formatação, lint, tipos, limites e design tokens."""

from __future__ import annotations

import ast
import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import check_limits
from gate_common import (
    BACKEND,
    FRONTEND,
    ROOT,
    LineSet,
    is_frontend_source,
    is_python_source,
    run,
    touches,
    venv_python,
)

RUFF_CONFIG = str(BACKEND / "pyproject.toml")
LEGACY_SELECT = "E,F,I,UP,B"
# Só o marcador `:linha: error: ` é uma regex; o arquivo e o texto saem por fatiamento. Um
# `^(.+?):(\d+): error: (.*)$` retrocede em tempo super-linear (Sonar S8786).
MYPY_MARKER_RE = re.compile(r":(?P<line>\d+): error: ")
MYPY_CODE_RE = re.compile(r"[\w-]+")
MYPY_BASELINE = ROOT / ".mypy-baseline.json"
MYPY_SUMMARY_RE = re.compile(r"^(Success:|Found \d+ errors?)", re.M)
# O ruff ancora estas regras na linha do `def`; vale a função inteira.
FUNCTION_LEVEL_CODES = {"C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915"}
MAX_DETAIL_LINES = 25
FORMAT_FRONTEND_NAME = "formatação frontend"


@dataclass
class StepResult:
    """Resultado de uma etapa do gate."""

    name: str
    ok: bool
    detail: list[str] = field(default_factory=list)


class MypyRunError(RuntimeError):
    """O mypy não executou corretamente (ausente, quebrado ou sem resumo)."""


MypyErrors = list[tuple[Path, int, str, str | None]]
Changed = dict[Path, LineSet]


def rel(path: Path | str) -> str:
    """Caminho relativo à raiz do repositório, para mensagens curtas."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def python_files(changed: Changed | None) -> list[Path]:
    """Arquivos Python a verificar: os alterados, ou todos quando `changed` é `None`."""
    if changed is not None:
        return sorted(p for p in changed if is_python_source(p))
    roots = [BACKEND, ROOT / "scripts", ROOT / ".claude" / "hooks"]
    found = [p for root in roots if root.exists() for p in root.rglob("*.py")]
    ignored = {".venv", "__pycache__", ".mypy_cache", ".ruff_cache"}
    return sorted(p for p in found if not ignored & set(p.parts))


def frontend_files(changed: Changed) -> list[Path]:
    """Arquivos de interface alterados."""
    return sorted(p for p in changed if is_frontend_source(p))


def needs_node() -> str | None:
    """Mensagem de erro se as dependências do frontend não estiverem instaladas."""
    if not (FRONTEND / "node_modules").exists():
        return "frontend/node_modules ausente: rode `npm ci` em frontend/"
    return None


def format_python(files: list[Path]) -> StepResult:
    """`ruff format --check` nos arquivos Python."""
    if not files:
        return StepResult("formatação Python", True)
    result = run(
        [
            venv_python(),
            "-m",
            "ruff",
            "format",
            "--check",
            "--config",
            RUFF_CONFIG,
            *map(str, files),
        ]
    )
    return StepResult("formatação Python", result.returncode == 0, tail(result.output))


def format_frontend(files: list[Path] | None) -> StepResult:
    """Prettier no frontend: em arquivos específicos ou no projeto inteiro (`None`)."""
    if files is not None and not files:
        return StepResult(FORMAT_FRONTEND_NAME, True)
    if missing := needs_node():
        return StepResult(FORMAT_FRONTEND_NAME, False, [missing])
    npx = shutil.which("npx") or "npx"
    targets = ["."] if files is None else [str(p.relative_to(FRONTEND)) for p in files]
    result = run([npx, "prettier", "--check", *targets], cwd=FRONTEND)
    return StepResult(FORMAT_FRONTEND_NAME, result.returncode == 0, tail(result.output))


def lint_legacy(files: list[Path]) -> StepResult:
    """Regras que o CI já exigia na árvore inteira (`E,F,I,UP,B`)."""
    cmd = [
        venv_python(),
        "-m",
        "ruff",
        "check",
        "--no-cache",
        "--config",
        RUFF_CONFIG,
        "--select",
        LEGACY_SELECT,
    ]
    result = run([*cmd, *map(str, files)], cwd=BACKEND)
    return StepResult("lint (base, árvore inteira)", result.returncode == 0, tail(result.output))


def lint_diff(files: list[Path], changed: Changed) -> StepResult:
    """Lint com todas as famílias do `pyproject`, mas só falha nas linhas alteradas."""
    name = "lint (todas as regras, linhas alteradas)"
    if not files:
        return StepResult(name, True)
    cmd = [
        venv_python(),
        "-m",
        "ruff",
        "check",
        "--no-cache",
        "--output-format",
        "json",
        "--config",
        RUFF_CONFIG,
    ]
    result = run([*cmd, *map(str, files)], cwd=BACKEND)
    try:
        findings = json.loads(result.output or "[]")
    except json.JSONDecodeError:
        return StepResult(name, False, tail(result.output))
    problems = []
    for item in findings:
        path = Path(item["filename"]).resolve()
        start, end = item["location"]["row"], item["end_location"]["row"]
        if item["code"] in FUNCTION_LEVEL_CODES:
            start, end = function_span(path, start)
        if touches(changed.get(path, frozenset()), start, end):
            problems.append(
                f"{rel(path)}:{item['location']['row']} {item['code']} {item['message']}"
            )
    return StepResult(name, not problems, problems[:MAX_DETAIL_LINES])


def function_span(path: Path, row: int) -> tuple[int, int]:
    """Intervalo de linhas da função que começa em `row` (ou apenas `row`, se não achar)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return row, row
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.lineno == row:
            return node.lineno, node.end_lineno or node.lineno
    return row, row


def mypy_key(path: Path, code: str | None, msg: str) -> str:
    """Chave de um erro do mypy sem número de linha (para a linha de base)."""
    return f"{rel(path)}|{code or '-'}|{msg}"


def split_mypy_code(text: str) -> tuple[str, str | None]:
    """Separa a mensagem do mypy do código final ``  [codigo]``; sem código, devolve `None`."""
    if text.endswith("]"):
        msg, separator, code = text[:-1].rpartition("  [")
        if separator and MYPY_CODE_RE.fullmatch(code):
            return msg, code
    return text, None


def split_mypy_line(raw: str) -> tuple[str, int, str] | None:
    """Divide `arquivo:linha: error: texto` em `(arquivo, linha, texto)`; outra linha, `None`.

    O arquivo tem ao menos um caractere e termina no primeiro marcador `:linha: error: `.
    """
    marker = MYPY_MARKER_RE.search(raw, 1)
    if marker is None:
        return None
    return raw[: marker.start()], int(marker["line"]), raw[marker.end() :]


def parse_mypy(cwd: Path, output: str) -> MypyErrors:
    """Extrai `(arquivo, linha, mensagem, código)` de cada erro do mypy."""
    errors = []
    for raw in output.splitlines():
        parts = split_mypy_line(raw)
        if parts:
            file, line, text = parts
            msg, code = split_mypy_code(text)
            errors.append(((cwd / file).resolve(), line, msg, code))
    return errors


def run_mypy(files: list[Path]) -> list[tuple[Path, MypyErrors]]:
    """Roda o mypy no backend e nas ferramentas; devolve os erros por diretório de execução.

    Raises:
        MypyRunError: Se o mypy não estiver instalado ou não produzir o resumo esperado.
    """
    py = venv_python()
    runs = []
    if any(BACKEND in p.parents for p in files):
        cmd = [py, "-m", "mypy", "--no-color-output", "app", "tests"]
        runs.append((BACKEND, run(cmd, cwd=BACKEND)))
    tools = [p for p in files if BACKEND not in p.parents]
    if tools:
        cmd = [
            py,
            "-m",
            "mypy",
            "--no-color-output",
            "--config-file",
            RUFF_CONFIG,
            *map(str, tools),
        ]
        runs.append((ROOT, run(cmd)))
    results = []
    for cwd, result in runs:
        if result.returncode not in (0, 1) or not MYPY_SUMMARY_RE.search(result.output):
            raise MypyRunError(
                "mypy não executou corretamente: " + " | ".join(tail(result.output)[-3:])
            )
        results.append((cwd, parse_mypy(cwd, result.output)))
    return results


def load_mypy_baseline() -> Counter[str]:
    """Erros de tipo já conhecidos (dívida técnica), por chave sem número de linha."""
    if not MYPY_BASELINE.exists():
        return Counter()
    return Counter(json.loads(MYPY_BASELINE.read_text(encoding="utf-8")))


def write_mypy_baseline() -> int:
    """Grava a linha de base com os erros atuais do mypy; devolve quantos são."""
    counts: Counter[str] = Counter()
    for _cwd, errors in run_mypy([BACKEND / "app" / "main.py"]):
        for path, _line, msg, code in errors:
            counts[mypy_key(path, code, msg)] += 1
    MYPY_BASELINE.write_text(
        json.dumps(dict(sorted(counts.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return sum(counts.values())


def types_python(files: list[Path], changed: Changed) -> StepResult:
    """Roda o mypy strict; falha em erro nas linhas alteradas ou fora da linha de base."""
    name = "tipos Python (mypy strict)"
    if not files:
        return StepResult(name, True)
    baseline = load_mypy_baseline()
    problems = []
    try:
        outcomes = run_mypy(files)
    except MypyRunError as exc:
        return StepResult(name, False, [str(exc)])
    for _cwd, errors in outcomes:
        seen: Counter[str] = Counter()
        for path, line, msg, code in errors:
            key = mypy_key(path, code, msg)
            seen[key] += 1
            is_new = seen[key] > baseline.get(key, 0)
            if is_new or touches(changed.get(path, frozenset()), line):
                problems.append(f"{rel(path)}:{line} {msg}  [{code}]")
    return StepResult(name, not problems, problems[:MAX_DETAIL_LINES])


def types_frontend() -> StepResult:
    """`tsc --noEmit` no frontend."""
    if missing := needs_node():
        return StepResult("tipos frontend (tsc)", False, [missing])
    npm = shutil.which("npm") or "npm"
    result = run([npm, "run", "--silent", "check"], cwd=FRONTEND)
    return StepResult("tipos frontend (tsc)", result.returncode == 0, tail(result.output))


def limits(files: list[Path], changed: Changed) -> StepResult:
    """Limites de tamanho e aninhamento, só nas linhas alteradas."""
    problems = []
    for path in files:
        for violation in check_limits.find_violations(path):
            if touches(changed.get(path.resolve(), frozenset()), violation.start, violation.end):
                problems.append(f"{rel(path)}:{violation.start} {violation.message}")
    return StepResult(
        "limites (função, aninhamento, módulo)",
        not problems,
        problems[:MAX_DETAIL_LINES],
    )


def design_tokens(files: list[Path] | None) -> StepResult:
    """Contraste AA e uso de cores/fontes fora dos tokens."""
    args = [] if files is None else [str(p) for p in files]
    if files is not None and not files:
        return StepResult("design system", True)
    result = run([venv_python(), str(ROOT / "scripts" / "check_design_tokens.py"), *args])
    return StepResult("design system", result.returncode == 0, tail(result.output))


def tail(output: str) -> list[str]:
    """Últimas linhas úteis de uma saída longa."""
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-MAX_DETAIL_LINES:]
