"""Hook SubagentStop (code-reviewer, qa-tester): registro do veredito.

Lê o relatório do subagent: a última mensagem de `SubagentHandback` no transcript do próprio
subagent (`agent_transcript_path`) ou, sem ela, `last_assistant_message`. Se o relatório não
seguir o formato fixo, bloqueia para o subagent completá-lo. Se seguir, grava o veredito, a data
e o fingerprint do código avaliado em `.claude/state/verdicts.json` e o relatório completo em
`.claude/reports/`.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import hook_common as common

VERDICT_RE = re.compile(r"^VEREDITO:\s*(APROVADO|REPROVADO)\s*$")
REQUIRED_SECTIONS = {
    "code-reviewer": ("Escopo:", "Gates:", "Problemas:"),
    "qa-tester": ("Testes:", "Critérios de aceite:", "Bugs:"),
}
VERDICTS_FILE = common.STATE_DIR / "verdicts.json"
HANDBACK_TOOL = "SubagentHandback"


def _line_handback(line: str) -> str | None:
    """Mensagem do `SubagentHandback` numa linha do transcript; `None` se ausente ou malformada."""
    try:
        entry = json.loads(line)
    except (ValueError, RecursionError):  # linha corrompida ou aninhada demais
        return None
    message = entry.get("message") if isinstance(entry, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("name") == HANDBACK_TOOL:
            payload = block.get("input")
            text = payload.get("message") if isinstance(payload, dict) else None
            return text if isinstance(text, str) else None
    return None


def handback_message(transcript_path: str) -> str | None:
    """Última mensagem enviada por `SubagentHandback` no transcript do subagent (JSONL).

    Quando o subagent entrega o relatório por essa ferramenta, `last_assistant_message` traz só
    um aviso de entrega. O `transcript_path` do hook é o da sessão principal e não serve aqui.
    O caminho vem do stdin: só aceita arquivo regular `.jsonl` e lê em streaming, sem falhar.
    """
    path = Path(transcript_path)
    if not transcript_path or path.suffix != ".jsonl":
        return None
    found: str | None = None
    try:
        if not path.is_file():  # no 3.11, `is_file` propaga ENAMETOOLONG/EACCES
            return None
        with path.open(encoding="utf-8", errors="replace") as transcript:
            for line in transcript:
                found = _line_handback(line) or found
    except OSError:
        return None
    return found


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
    message = handback_message(str(data.get("agent_transcript_path", ""))) or str(
        data.get("last_assistant_message", "")
    )
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
