"""Utilitários dos testes dos scripts de CI (`scripts/ci/`)."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
CI_DIR = ROOT / "scripts" / "ci"


def load_ci_module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, CI_DIR / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603  # git fixo; argumentos escritos nos próprios testes
        ["git", *args],  # noqa: S607  # git do PATH da máquina de teste
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)
    return path


def run_script(
    script: str, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # script do próprio repositório; argumentos dos testes
        [str(CI_DIR / script), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        cwd=ROOT,
        check=False,
    )
