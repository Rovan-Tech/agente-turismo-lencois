"""Gate de qualidade único: os mesmos comandos rodam nos hooks, subagents, pre-commit e CI.

Uso:
    python scripts/quality_gate.py --fast                 # só o que mudou (segundos)
    python scripts/quality_gate.py --full                 # tudo, incluindo testes e E2E
    python scripts/quality_gate.py --fast --files a.py    # restringe a arquivos específicos
    python scripts/quality_gate.py --full --update-baseline   # sobe a linha de base de cobertura
    python scripts/quality_gate.py --full --scope backend     # só backend (usado pelo CI)

Sai com código diferente de zero se qualquer etapa falhar.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml  # noqa: E501
from pathlib import Path

import gate_steps as steps
from gate_common import (
    BACKEND,
    FRONTEND,
    ROOT,
    base_ref,
    changed_lines,
    run,
    touches,
    venv_python,
)
from gate_steps import StepResult

BASELINE_FILE = ROOT / ".coverage-baseline.json"
MIN_DIFF_COVERAGE = 90


def _npm() -> str:
    return shutil.which("npm") or "npm"


def _npx() -> str:
    return shutil.which("npx") or "npx"


def backend_coverage(xml_path: Path) -> float:
    """Cobertura total (linhas + ramos) do `coverage.xml`, em porcentagem."""
    # nosemgrep: python.lang.security.use-defused-xml-parse.use-defused-xml-parse  # noqa: ERA001
    root = ET.parse(xml_path).getroot()  # noqa: S314  # arquivo gerado localmente pelo pytest-cov
    valid = int(root.attrib["lines-valid"]) + int(root.attrib.get("branches-valid", 0))
    covered = int(root.attrib["lines-covered"]) + int(root.attrib.get("branches-covered", 0))
    return 100.0 * covered / valid if valid else 100.0


def tests_backend() -> tuple[StepResult, float | None]:
    """Roda o pytest com cobertura; retorna a etapa e a cobertura total."""
    cmd = [
        venv_python(),
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--cov",
        "--cov-report=xml:coverage.xml",
    ]
    result = run(cmd, cwd=BACKEND)
    name = "testes backend (pytest)"
    if result.returncode != 0:
        return StepResult(name, False, steps.tail(result.output)), None
    return StepResult(name, True), backend_coverage(BACKEND / "coverage.xml")


def tests_frontend() -> tuple[StepResult, float | None]:
    """Roda o Vitest com cobertura; retorna a etapa e a cobertura de linhas."""
    name = "testes frontend (vitest)"
    if missing := steps.needs_node():
        return StepResult(name, False, [missing]), None
    result = run([_npm(), "run", "--silent", "test:unit", "--", "--coverage"], cwd=FRONTEND)
    if result.returncode != 0:
        return StepResult(name, False, steps.tail(result.output)), None
    summary = json.loads(
        (FRONTEND / "coverage" / "coverage-summary.json").read_text(encoding="utf-8")
    )
    return StepResult(name, True), float(summary["total"]["lines"]["pct"])


def coverage_baseline(current: dict[str, float | None], update: bool) -> StepResult:
    """A cobertura global nunca pode cair abaixo da linha de base."""
    name = "cobertura global >= linha de base"
    baseline = (
        json.loads(BASELINE_FILE.read_text(encoding="utf-8")) if BASELINE_FILE.exists() else {}
    )
    problems = []
    for key, value in current.items():
        if value is None:
            continue
        if value + 0.01 < baseline.get(key, 0.0):
            problems.append(f"{key}: {value:.2f}% < baseline {baseline[key]:.2f}%")
        elif update:
            baseline[key] = round(max(value, baseline.get(key, 0.0)), 2)
    if update and not problems:
        BASELINE_FILE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    return StepResult(name, not problems, problems)


def diff_coverage(base: str, reports: list[Path]) -> StepResult:
    """Cobertura mínima nas linhas alteradas (`diff-cover`)."""
    name = f"cobertura das linhas alteradas >= {MIN_DIFF_COVERAGE}%"
    existing = [str(p) for p in reports if p.exists()]
    if not existing:
        return StepResult(name, False, ["nenhum relatório de cobertura gerado"])
    cmd = [venv_python(), "-m", "diff_cover.diff_cover_tool", *existing]
    cmd += [
        "--compare-branch",
        base,
        "--fail-under",
        str(MIN_DIFF_COVERAGE),
        "--include-untracked",
    ]
    result = run(cmd)
    return StepResult(name, result.returncode == 0, steps.tail(result.output))


def duplication(changed: steps.Changed) -> StepResult:
    """Blocos duplicados com 6+ linhas nas linhas alteradas (jscpd; config em `.jscpd.json`)."""
    name = "duplicação (jscpd, linhas alteradas)"
    binary = FRONTEND / "node_modules" / ".bin" / "jscpd"
    if not binary.exists():
        return StepResult(name, False, ["jscpd ausente: rode `npm ci` em frontend/"])
    with tempfile.TemporaryDirectory() as out:
        cmd = [str(binary), "--config", str(ROOT / ".jscpd.json"), "--silent"]
        result = run([*cmd, "--reporters", "json", "--output", out], cwd=ROOT)
        report = Path(out) / "jscpd-report.json"
        if not report.exists():
            return StepResult(
                name, False, steps.tail(result.output) or ["jscpd não gerou relatório"]
            )
        clones = json.loads(report.read_text(encoding="utf-8"))["duplicates"]
    problems = []
    for clone in clones:
        first, second = clone["firstFile"], clone["secondFile"]
        for mine, other in ((first, second), (second, first)):
            path = Path(mine["name"]).resolve()
            if path in changed and touches(changed[path], mine["start"], mine["end"]):
                where = f"{steps.rel(other['name'])}:{other['start']}"
                head = f"{steps.rel(path)}:{mine['start']}"
                problems.append(f"{head} {clone['lines']} linhas duplicadas de {where}")
    return StepResult(name, not problems, sorted(set(problems))[: steps.MAX_DETAIL_LINES])


def dead_code() -> StepResult:
    """Código morto (vulture; config em `backend/pyproject.toml`)."""
    result = run([venv_python(), "-m", "vulture"], cwd=BACKEND)
    return StepResult("código morto (vulture)", result.returncode == 0, steps.tail(result.output))


def security_backend() -> list[StepResult]:
    """Executa o bandit e o pip-audit."""
    py = venv_python()
    checks = [
        ("segurança estática (bandit)", [py, "-m", "bandit", "-r", "app", "-q"]),
        (
            "auditoria de dependências Python (pip-audit)",
            [py, "-m", "pip_audit", "-r", "requirements-dev.txt"],
        ),
    ]
    outcomes = [(name, run(cmd, cwd=BACKEND)) for name, cmd in checks]
    return [StepResult(n, o.returncode == 0, steps.tail(o.output)) for n, o in outcomes]


def security_frontend() -> StepResult:
    """Executa o `npm audit` (severidade alta ou pior)."""
    outcome = run([_npm(), "audit", "--audit-level=high"], cwd=FRONTEND)
    return StepResult(
        "auditoria de dependências npm",
        outcome.returncode == 0,
        steps.tail(outcome.output),
    )


def build_and_e2e() -> list[StepResult]:
    """Build de produção do painel e suíte E2E completa (Playwright)."""
    results = []
    for name, script in (("build frontend", "build"), ("E2E (Playwright)", "test:e2e")):
        outcome = run([_npm(), "run", "--silent", script], cwd=FRONTEND, timeout=1200)
        results.append(StepResult(name, outcome.returncode == 0, steps.tail(outcome.output)))
    return results


def run_fast(changed: steps.Changed) -> list[StepResult]:
    """Gate rápido: só arquivos alterados."""
    py = steps.python_files(changed)
    fe = steps.frontend_files(changed)
    results = [
        steps.format_python(py),
        steps.format_frontend(fe),
        steps.lint_diff(py, changed),
    ]
    results.append(steps.types_python(py, changed))
    if any(p.suffix in {".ts", ".tsx"} for p in fe):
        results.append(steps.types_frontend())
    results += [steps.limits(py, changed), steps.design_tokens(fe)]
    if py or fe:
        results.append(duplication(changed))
    return results


def full_backend(changed: steps.Changed, base: str, update_baseline: bool) -> list[StepResult]:
    """Etapas completas do backend (Python do backend, scripts e hooks)."""
    py_all = steps.python_files(None)
    py_changed = steps.python_files(changed)
    results = [steps.format_python(py_all), steps.lint_legacy(py_all)]
    results += [
        steps.lint_diff(py_changed, changed),
        steps.types_python(py_changed, changed),
    ]
    results.append(steps.limits(py_changed, changed))
    tests, pct = tests_backend()
    results += [tests, coverage_baseline({"backend": pct}, update_baseline)]
    results += [
        diff_coverage(base, [BACKEND / "coverage.xml"]),
        dead_code(),
        *security_backend(),
    ]
    return results


def full_frontend(changed: steps.Changed, base: str, update_baseline: bool) -> list[StepResult]:
    """Etapas completas do frontend (painel React); a duplicação roda aqui por causa do Node."""
    results = [
        steps.format_frontend(None),
        steps.types_frontend(),
        steps.design_tokens(None),
    ]
    tests, pct = tests_frontend()
    results += [tests, coverage_baseline({"frontend": pct}, update_baseline)]
    cobertura = FRONTEND / "coverage" / "cobertura-coverage.xml"
    results += [
        diff_coverage(base, [cobertura]),
        duplication(changed),
        security_frontend(),
    ]
    results += build_and_e2e()
    return results


def run_full(
    changed: steps.Changed, base: str, update_baseline: bool, scope: str
) -> list[StepResult]:
    """Gate completo, no escopo pedido (`backend`, `frontend` ou `all`)."""
    results: list[StepResult] = []
    if scope in {"backend", "all"}:
        results += full_backend(changed, base, update_baseline)
    if scope in {"frontend", "all"}:
        results += full_frontend(changed, base, update_baseline)
    return results


def report(results: list[StepResult], elapsed: float, mode: str) -> int:
    """Imprime o resumo (✅/❌ por etapa, detalhe só do que falhou) e devolve o código de saída."""
    out = []
    for result in results:
        out.append(f"{'✅' if result.ok else '❌'} {result.name}")
        if not result.ok:
            out.extend(f"    {line}" for line in result.detail)
    failed = [r for r in results if not r.ok]
    verdict = "VERDE" if not failed else f"{len(failed)} etapa(s) com falha"
    passed = len(results) - len(failed)
    out.append(f"\nGate {mode}: {verdict} ({passed}/{len(results)} etapas, {elapsed:.1f}s)")
    sys.stdout.write("\n".join(out) + "\n")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    """Ponto de entrada do gate."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fast", action="store_true", help="só arquivos alterados")
    mode.add_argument("--full", action="store_true", help="tudo")
    parser.add_argument("--base", default=None, help="branch base do diff (padrão: origin/main)")
    parser.add_argument("--files", nargs="*", default=None, help="restringe a estes arquivos")
    parser.add_argument(
        "--write-mypy-baseline", action="store_true", help="regrava .mypy-baseline.json"
    )
    parser.add_argument(
        "--scope", choices=["all", "backend", "frontend"], default="all", help="só com --full"
    )
    parser.add_argument(
        "--update-baseline", action="store_true", help="sobe a linha de base de cobertura"
    )
    args = parser.parse_args(argv)
    if args.write_mypy_baseline:
        count = steps.write_mypy_baseline()
        sys.stdout.write(f".mypy-baseline.json regravado com {count} erro(s)\n")
        return 0
    if not (args.fast or args.full):
        parser.error("informe --fast ou --full")

    start = time.monotonic()
    base = args.base or base_ref()
    changed = changed_lines(base)
    if args.files is not None:
        wanted = {Path(f).resolve() for f in args.files}
        changed = {p: changed.get(p, frozenset()) for p in wanted if p.exists()}
    results = (
        run_fast(changed)
        if args.fast
        else run_full(changed, base, args.update_baseline, args.scope)
    )
    return report(results, time.monotonic() - start, "rápido" if args.fast else "completo")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
