"""Hook Stop: portão final do fluxo obrigatório.

Se o código mudou nesta sessão (fingerprint atual diferente do registrado no início, o que pega até
edições feitas via Bash), ainda há alterações pendentes e não existem vereditos APROVADO do
code-reviewer e do qa-tester para o fingerprint atual, impede a parada. Para não criar loop
infinito: após 3 bloqueios seguidos sem progresso, libera com um aviso explícito.
"""

from __future__ import annotations

import sys

import hook_common as common

MAX_BLOCKS = 3


def missing_approvals(current: str) -> list[str]:
    """Subagents sem APROVADO para o fingerprint atual."""
    state = common.read_json(common.STATE_DIR / "verdicts.json", {})
    missing = []
    for agent in common.REVIEW_AGENTS:
        info = state.get(agent) or {}
        if info.get("verdict") != "APROVADO" or info.get("fingerprint") != current:
            missing.append(agent)
    return missing


def progress_key(current: str, missing: list[str]) -> str:
    """Identifica o "estado" da sessão: se mudar entre bloqueios, houve progresso."""
    return f"{current}|{','.join(missing)}"


def main() -> int:
    """Decide se a resposta pode terminar."""
    data = common.read_input()
    session = str(data.get("session_id", "unknown"))
    digest, files = common.fingerprint()
    start = common.read_json(common.STATE_DIR / f"session-{session}.json", None)
    counter_file = common.STATE_DIR / f"stop-{session}.json"
    if start is None or not files or start.get("fingerprint") == digest:
        counter_file.unlink(missing_ok=True)
        return 0
    missing = missing_approvals(digest)
    if not missing:
        counter_file.unlink(missing_ok=True)
        return 0
    key = progress_key(digest, missing)
    counter = common.read_json(counter_file, {})
    blocks = counter.get("blocks", 0) + 1 if counter.get("key") == key else 1
    if blocks > MAX_BLOCKS:
        counter_file.unlink(missing_ok=True)
        common.emit(
            {
                "systemMessage": (
                    f"AVISO: liberando a parada após {MAX_BLOCKS} bloqueios sem progresso. "
                    f"Falta APROVADO de: {', '.join(missing)}. Fluxo obrigatório NÃO concluído."
                )
            }
        )
        return 0
    common.write_json(counter_file, {"key": key, "blocks": blocks})
    common.fail_message(
        {},
        "Código alterado sem aprovação completa. Faltam vereditos APROVADO para o código atual de: "
        + ", ".join(missing)
        + ". Rode o gate rápido, invoque o code-reviewer e depois o qa-tester (briefing completo) "
        "e corrija o que reprovarem: qualquer FALHA no checklist "
        "(docs/checklist-engenharia.md) é REPROVADO. "
        f"(bloqueio {blocks}/{MAX_BLOCKS})",
    )
    return 0


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "stop_gate"))
