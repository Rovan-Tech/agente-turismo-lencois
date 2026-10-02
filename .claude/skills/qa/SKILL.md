---
name: qa
description: Roda o qa-tester (gate completo, E2E e teste exploratório com Playwright MCP). Use para validar o estado atual do painel ou um fluxo.
disable-model-invocation: true
---

# /qa

1. Briefing curto: objetivo, critérios de aceite (pergunte ao Patrick se não estiverem claros),
   arquivos alterados e como subir o app (backend `uvicorn app.main:app` em `backend/`; painel
   `npm run build && npm run preview` em `frontend/`).
2. Invoque o subagent `qa-tester` com esse briefing.
3. Apresente o relatório. Se REPROVADO, cada bug vira teste que falha antes da correção (`/bugfix`).
