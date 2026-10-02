---
name: feature
description: Implementa uma funcionalidade de forma proporcional ao risco (entender, ADR/threat model se couber, implementar com testes, gate rápido, revisão só se for de risco). Use quando o Patrick pedir uma funcionalidade nova ou mudança de comportamento.
argument-hint: "<descrição da funcionalidade>"
disable-model-invocation: true
---

# /feature

Tarefa: **$ARGUMENTS**

1. **Entender.** Critérios de aceite em poucas linhas testáveis. Se for grande ou ambígua, um plano
   curto e a aprovação do Patrick antes de codar.
2. **Antes do código, só se couber:** mudança arquitetural (banco, biblioteca de infra, padrão de
   comunicação, provedor de LLM) → `/adr` e espere a aprovação; funcionalidade crítica nova
   (endpoint, webhook, auth, dado pessoal, LLM) → `/threat-model` curto, mitigações viram testes.
3. **Implementar com testes** numa branch `feat/...` (nunca na `main`), seguindo `.claude/rules/`.
   Mudança visível no painel pede spec Playwright; superfície de ataque, teste de segurança.
4. **Gate rápido:** `python3 scripts/quality_gate.py --fast` até ficar verde.
5. **Revisão só se for de risco** (auth, webhook, dado pessoal, LLM, migração, infra, mudança
   grande): `/revisar`; `/qa` se for visual/de fluxo. Corrija os BLOQUEANTES e IMPORTANTES e
   revise **uma vez** de novo; não faça rodadas em cadeia.
6. **Entrega:** resumo do que mudou e por quê, o que foi verificado, pendências. Sem commit/push sem
   autorização do Patrick.
