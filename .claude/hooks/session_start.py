"""Hook SessionStart: fingerprint inicial e contexto curto para a sessão.

Registra o fingerprint do código no começo da sessão (sem sobrescrever em resume/compact) e injeta
branch, git status, últimos vereditos (e se ainda valem) e o lembrete do fluxo obrigatório.
"""

from __future__ import annotations

import sys

import hook_common as common

REMINDER = (
    "Fluxo obrigatório para alterar código: implementar com testes -> gate rápido "
    "(make gate-fast) -> subagent code-reviewer -> subagent qa-tester -> "
    "entregar. Qualquer mudança de código invalida as aprovações. Sem commit/push sem autorização."
)


def verdict_lines(current: str) -> list[str]:
    """Últimos vereditos e se ainda valem para o código atual."""
    state = common.read_json(common.STATE_DIR / "verdicts.json", {})
    lines = []
    for agent in common.REVIEW_AGENTS:
        info = state.get(agent)
        if not info:
            lines.append(f"- {agent}: sem veredito registrado")
            continue
        valid = (
            "vale para o código atual" if info.get("fingerprint") == current else "DESATUALIZADO"
        )
        lines.append(f"- {agent}: {info.get('verdict')} em {info.get('at')} ({valid})")
    return lines


def main() -> int:
    """Grava o fingerprint inicial e injeta o resumo de contexto."""
    data = common.read_input()
    session = str(data.get("session_id", "unknown"))
    digest, files = common.fingerprint()
    session_file = common.STATE_DIR / f"session-{session}.json"
    if not session_file.exists():
        common.write_json(session_file, {"fingerprint": digest, "files": files})
    status = common.git("status", "--short") or "(limpo)"
    branch = common.current_branch() or "(desconhecida)"
    lines = [
        f"Branch: {branch}",
        f"git status:\n{status}",
        "Vereditos dos subagents:",
        *verdict_lines(digest),
        REMINDER,
    ]
    context = "\n".join(lines)
    common.emit(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    )
    return 0


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "session_start"))
