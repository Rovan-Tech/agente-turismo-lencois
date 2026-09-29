---
name: qa
description: Roda só o qa-tester (gate completo, E2E e testes exploratórios com Playwright MCP). Use depois que o código foi revisado, ou para validar o estado atual do painel.
disable-model-invocation: true
---

# /qa

1. Reúna o briefing: objetivo, critérios de aceite (pergunte ao Patrick se não estiverem claros),
   arquivos alterados (`git diff --stat $(git merge-base HEAD origin/main)`), branch base
   `origin/main`, como subir o app (backend `uvicorn app.main:app` em `backend/`; painel
   `npm run build && npm run preview` em `frontend/`) e como rodar os testes.
2. Invoque o subagent `qa-tester` com esse briefing (e, a partir da 2ª rodada, o que mudou).
3. Apresente o relatório integralmente. Se REPROVADO, transforme cada bug em teste que falha antes
   de corrigir (fluxo de `/bugfix`) e lembre que a correção invalida a aprovação do `code-reviewer`.
