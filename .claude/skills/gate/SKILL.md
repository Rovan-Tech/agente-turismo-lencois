---
name: gate
description: Roda o gate de qualidade completo (formatação, lint, tipos, testes com cobertura, cobertura do diff, duplicação, código morto, auditoria de dependências, build e E2E) e resume o resultado.
disable-model-invocation: true
allowed-tools: Bash(python3 scripts/quality_gate.py *) Bash(backend/.venv/bin/python3 scripts/quality_gate.py *) Bash(make gate*)
---

# /gate

1. Rode `python3 scripts/quality_gate.py --full` (use `backend/.venv/bin/python` se o venv existir;
   `make gate` é equivalente). Pode levar de 20 s a alguns minutos.
2. Resuma: etapas ✅/❌, cobertura total (backend e frontend) e do diff, e para cada ❌ o motivo em
   uma linha e o arquivo:linha principal.
3. **Não corrija nada por conta própria** além de trivialidades óbvias que o Patrick pediu; se algo
   falhar, proponha a correção. Nunca rebaixe limites nem edite configs para passar.
4. Se faltar dependência (`npm ci`, `npx playwright install chromium`, venv), diga o comando.

## Relação com o checklist

O gate cobre os itens automatizáveis de `docs/checklist-engenharia.md` (`GATE-1`..`GATE-4`,
parte de `PY-2`, `SEC-4` (bandit e ruff `S`; o Semgrep roda no CI), `SEC-5`, `FE-8`). Gate verde **não** aprova sozinho: o `code-reviewer` e o
`qa-tester` ainda preenchem o checklist inteiro.
