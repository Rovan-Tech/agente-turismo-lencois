"""Decide quais jobs do CI precisam rodar, a partir dos arquivos que o PR alterou.

O job `ci-ok` trata job pulado como sucesso, então só pulamos o que o diff certamente não afeta:
um PR apenas de documentação. Um caminho que nenhum grupo reconhece (hooks, baselines, config de
qualidade, arquivo novo na raiz) faz tudo rodar, e o mesmo vale se não der para comparar (push,
fila de merge, falha do git): na dúvida, roda.

Uso: python scripts/ci/changes.py --base <sha> --head <sha>   # imprime `grupo=true|false`
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_CI_WORKFLOW = ".github/workflows/ci.yml"

# Grupo -> prefixos de caminho que o afetam.
_GROUPS: dict[str, tuple[str, ...]] = {
    "backend": ("backend/", "scripts/", _CI_WORKFLOW),
    "frontend": ("frontend/", "scripts/", _CI_WORKFLOW),
    "docker": (
        "backend/app/",
        "backend/alembic",
        "backend/Dockerfile",
        "backend/requirements",
        ".hadolint.yaml",
        _CI_WORKFLOW,
    ),
    "deps": (
        "backend/requirements",
        "frontend/package.json",
        "frontend/package-lock.json",
        _CI_WORKFLOW,
    ),
    "workflows": (".github/", "scripts/ci/"),
}
# Mudar o próprio pipeline (`scripts/ci/`) reexecuta tudo que ele roda, mas não afeta o gate.
_CI_SCRIPTS = "scripts/ci/"
_REEXECUTED_BY_CI_SCRIPTS = frozenset({"backend", "frontend", "workflows"})
# Os dois scripts que o job `docker` executa contra o container.
_DOCKER_CI_SCRIPTS = frozenset({"scripts/ci/smoke.sh", "scripts/ci/wait_for_url.sh"})


def _affects(group: str, path: str) -> bool:
    if path.startswith(_CI_SCRIPTS):
        return group in _REEXECUTED_BY_CI_SCRIPTS or (
            group == "docker" and path in _DOCKER_CI_SCRIPTS
        )
    return path.startswith(_GROUPS[group])


_DOCS_READ_BY_TESTS = frozenset({"docs/checklist-engenharia.md", "docs/tech-debt.md"})


def _is_docs(path: str) -> bool:
    """Diz se o arquivo é documentação pura, que não muda comportamento.

    Valem como código: o que está em `.claude/`, o checklist (define o que o gate exige) e a dívida
    técnica (um teste confere que todo item ⏳ do checklist cita um `TD-*` que existe).
    """
    if path.startswith(".claude/") or path in _DOCS_READ_BY_TESTS:
        return False
    return path.startswith("docs/") or path.endswith(".md")


def classify(paths: list[str] | None) -> dict[str, bool]:
    """Para cada grupo, diz se algum caminho alterado o afeta.

    `None` (não sei comparar) e qualquer caminho que nenhum grupo reconhece ligam todos os grupos.
    """
    if paths is None:
        return dict.fromkeys(_GROUPS, True)
    relevant = [path for path in paths if not _is_docs(path)]
    if any(not any(_affects(group, path) for group in _GROUPS) for path in relevant):
        return dict.fromkeys(_GROUPS, True)
    return {group: any(_affects(group, path) for path in relevant) for group in _GROUPS}


# SHA, `HEAD` ou nome de ref; nunca começa com `-` (viraria opção do git).
_REF = re.compile(r"^(?!-)[A-Za-z0-9._/~^-]{1,100}$")


def changed_files(base: str, head: str, cwd: Path | None = None) -> list[str] | None:
    """Arquivos alterados entre `base` e `head`; `None` se o git não conseguir comparar."""
    if not (_REF.fullmatch(base) and _REF.fullmatch(head)):
        return None
    command = [
        "git",
        "-c",
        "core.quotepath=false",
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        f"{base}...{head}",
    ]
    try:
        output = subprocess.run(  # noqa: S603  # git fixo; base e head validados contra `_REF`
            command, cwd=cwd, check=True, capture_output=True, text=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [path for path in output.split("\0") if path]


def main(argv: list[str]) -> int:
    """Imprime os grupos no formato que o `$GITHUB_OUTPUT` entende."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    paths = changed_files(args.base, args.head) if args.base else None
    for group, needed in classify(paths).items():
        sys.stdout.write(f"{group}={'true' if needed else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
