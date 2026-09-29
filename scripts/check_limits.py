"""Mede os limites objetivos de `.claude/rules/python.md`: tamanho de função, aninhamento e módulo.

Complexidade ciclomática e número de parâmetros ficam com o ruff (`C901`, `PLR0913`).

Uso:
    python scripts/check_limits.py arquivo.py [...]
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_FUNCTION_LINES = 40
MAX_NESTING = 3
MAX_MODULE_LINES = 400
NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class LimitViolation:
    """Violação de um limite, com o intervalo de linhas a que se refere."""

    path: Path
    start: int
    end: int
    message: str


def _body_lines(node: FunctionNode) -> int:
    """Linhas do corpo da função, sem contar a docstring."""
    body = node.body
    first = body[0]
    has_doc = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    doc_lines = (first.end_lineno or first.lineno) - first.lineno + 1 if has_doc else 0
    return (node.end_lineno or node.lineno) - node.lineno + 1 - doc_lines


def _max_depth(node: ast.AST, depth: int = 0) -> int:
    """Maior profundidade de blocos aninhados dentro de `node`."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            continue
        is_elif = isinstance(node, ast.If) and isinstance(child, ast.If) and node.orelse == [child]
        step = depth + 1 if isinstance(child, NESTING_NODES) and not is_elif else depth
        deepest = max(deepest, _max_depth(child, step))
    return deepest


def find_violations(path: Path) -> list[LimitViolation]:
    """Lista as violações de limite de um arquivo Python."""
    source = path.read_text(encoding="utf-8")
    violations: list[LimitViolation] = []
    total = len(source.splitlines())
    if total > MAX_MODULE_LINES:
        violations.append(
            LimitViolation(path, 1, total, f"módulo com {total} linhas (máx. {MAX_MODULE_LINES})")
        )
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        end = node.end_lineno or node.lineno
        size = _body_lines(node)
        if size > MAX_FUNCTION_LINES:
            violations.append(
                LimitViolation(
                    path,
                    node.lineno,
                    end,
                    f"{node.name}: {size} linhas (máx. {MAX_FUNCTION_LINES})",
                )
            )
        depth = _max_depth(node)
        if depth > MAX_NESTING:
            violations.append(
                LimitViolation(
                    path, node.lineno, end, f"{node.name}: aninhamento {depth} (máx. {MAX_NESTING})"
                )
            )
    return violations


def main(argv: list[str]) -> int:
    """Ponto de entrada: imprime as violações e retorna 1 se houver alguma."""
    found = [v for arg in argv for v in find_violations(Path(arg))]
    for violation in found:
        sys.stdout.write(f"{violation.path}:{violation.start} — {violation.message}\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
