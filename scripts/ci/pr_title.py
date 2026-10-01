"""Valida que o título do PR segue Conventional Commits (o squash usa o título como mensagem).

Uso: python scripts/ci/pr_title.py "feat: descrição curta"
"""

from __future__ import annotations

import re
import sys

_TYPES = "feat|fix|refactor|test|docs|chore|ci|perf|build|revert|style"
_PATTERN = re.compile(rf"^(?:{_TYPES})(?:\([a-z0-9._/-]+\))?!?: \S.{{0,99}}$")


def is_valid(title: str) -> bool:
    """`tipo(escopo opcional)!: descrição`: tipo em minúsculas, descrição de até 100 caracteres."""
    return _PATTERN.fullmatch(title) is not None


def main(argv: list[str]) -> int:
    """Sai com 1 e explica o formato esperado quando o título é inválido."""
    title = argv[0] if argv else ""
    if is_valid(title):
        sys.stdout.write("Título do PR no padrão Conventional Commits.\n")
        return 0
    sys.stderr.write(
        f"::error::Título do PR fora do padrão: {title!r}. Use `tipo: descrição` com tipo em "
        f"({_TYPES.replace('|', ', ')}); ex.: `feat: add booking calendar`.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
