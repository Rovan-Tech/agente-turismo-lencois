"""Hook SubagentStop (code-reviewer, qa-tester): registro do veredito.

Lê `last_assistant_message`. Se o relatório não seguir o formato fixo, bloqueia para o subagent
completá-lo. Se seguir, grava o veredito, a data e o fingerprint do código avaliado em
`.claude/state/verdicts.json` e o relatório completo em `.claude/reports/`.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime

import hook_common as common

VERDICT_RE = re.compile(r"^VEREDITO:\s*(APROVADO|REPROVADO)\s*$")
REQUIRED_SECTIONS = {
    "code-reviewer": ("Escopo:", "Gates:", "Problemas:"),
    "qa-tester": ("Testes:", "Critérios de aceite:", "Bugs:"),
}
VERDICTS_FILE = common.STATE_DIR / "verdicts.json"


def parse_report(agent: str, message: str) -> tuple[str | None, str]:
    """Valida o relatório e devolve `(veredito, motivo_da_rejeição)`."""
    lines = [line for line in message.strip().splitlines() if line.strip()]
    match = VERDICT_RE.match(lines[0].strip()) if lines else None
    if not match:
        return (
            None,
            "A primeira linha deve ser exatamente `VEREDITO: APROVADO` ou `VEREDITO: REPROVADO`.",
        )
    missing = [s for s in REQUIRED_SECTIONS.get(agent, ()) if s not in message]
    if missing:
        return None, "Relatório incompleto: faltam as seções " + ", ".join(missing) + "."
    return match.group(1), ""


def reconcile_with_start(
    agent_id: str, verdict: str | None, current: str
) -> tuple[str | None, str]:
    """Usa o fingerprint do INÍCIO da revisão; se o código mudou nela, invalida o veredito."""
    starts = common.read_json(common.STARTS_FILE, {})
    start = starts.pop(agent_id, None) if agent_id else None
    common.write_json(common.STARTS_FILE, starts)
    if not start:
        return verdict, current
    if start.get("fingerprint") != current:
        return None, str(start.get("fingerprint"))
    return verdict, current


def main() -> int:
    """Registra o veredito do subagent que acabou de terminar."""
    data = common.read_input()
    agent = str(data.get("agent_type", ""))
    if agent not in common.REVIEW_AGENTS:
        return 0
    message = str(data.get("last_assistant_message", ""))
    verdict, reason = parse_report(agent, message)
    already_retried = bool(data.get("stop_hook_active"))
    if verdict is None and not already_retried:
        common.fail_message(
            {}, reason + " Reescreva o relatório final no formato fixo do seu prompt."
        )
        return 0
    stamp = datetime.now(UTC)
    digest, files = common.fingerprint()
    verdict, digest = reconcile_with_start(str(data.get("agent_id", "")), verdict, digest)
    state = common.read_json(VERDICTS_FILE, {})
    state[agent] = {
        "verdict": verdict or "INVALIDO",
        "at": stamp.isoformat(timespec="seconds"),
        "fingerprint": digest,
        "files": files,
    }
    common.write_json(VERDICTS_FILE, state)
    common.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = common.REPORTS_DIR / f"{stamp.strftime('%Y%m%dT%H%M%SZ')}-{agent}.md"
    report.write_text(message, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "record_verdict"))
