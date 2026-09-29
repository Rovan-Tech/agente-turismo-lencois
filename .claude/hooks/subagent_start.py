"""Hook SubagentStart (code-reviewer, qa-tester): carimba o código no INÍCIO da revisão.

O veredito vale para o código que o subagent viu ao começar. Se o agente principal editar arquivos
enquanto o subagent roda em background, o `record_verdict` percebe e invalida o veredito.
"""

from __future__ import annotations

import sys

import hook_common as common

MAX_ENTRIES = 50


def main() -> int:
    """Grava o fingerprint atual associado ao `agent_id`."""
    data = common.read_input()
    agent_id = str(data.get("agent_id", ""))
    if str(data.get("agent_type", "")) not in common.REVIEW_AGENTS or not agent_id:
        return 0
    digest, _files = common.fingerprint()
    starts = common.read_json(common.STARTS_FILE, {})
    starts[agent_id] = {"fingerprint": digest, "agent": data.get("agent_type")}
    for old in list(starts)[:-MAX_ENTRIES]:
        starts.pop(old)
    common.write_json(common.STARTS_FILE, starts)
    return 0


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "subagent_start"))
