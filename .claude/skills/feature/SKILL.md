---
name: feature
description: Implementa uma funcionalidade seguindo o fluxo obrigatório do projeto (entender, pesquisar no context7, implementar com testes, gate rápido, code-reviewer, qa-tester, relatório final). Use quando o Patrick pedir uma funcionalidade nova ou uma mudança de comportamento.
argument-hint: "<descrição da funcionalidade>"
disable-model-invocation: true
---

# /feature

Tarefa: **$ARGUMENTS**

Execute o fluxo do `CLAUDE.md` (seção "Fluxo obrigatório") do começo ao fim, sem pular etapas.
Acompanhe cada etapa com a lista de tarefas.

1. **Entender.** Escreva os critérios de aceite (testáveis, um por linha). Se a tarefa for grande ou
   ambígua, apresente um plano curto e peça aprovação antes de codar.
2. **Pesquisar.** Para cada biblioteca envolvida, consulte o context7 (`resolve-library-id` →
   `query-docs`). Não confie na memória para APIs.
3. **Implementar com testes** (TDD quando viável: teste falhando → código → refatoração), seguindo
   `.claude/rules/`. Mudança visível no painel exige spec Playwright; superfície de ataque exige teste
   em `test_security.py`. Trabalhe numa branch `feat/...` (nunca na `main`).
4. **Gate rápido.** `python3 scripts/quality_gate.py --fast` até ficar verde. Nunca silencie erro.
5. **Revisão.** Invoque o subagent `code-reviewer` com o briefing completo: objetivo, critérios de
   aceite, arquivos alterados e branch base (`origin/main`), como subir o app e rodar os testes e, a
   partir da 2ª rodada, o que mudou desde o último relatório. REPROVADO → corrija todos os
   BLOQUEANTES e IMPORTANTES e invoque de novo.
6. **QA.** Com a revisão aprovada, invoque `qa-tester` com o mesmo briefing. REPROVADO → transforme
   cada bug num teste que falha, corrija e **volte ao passo 5**: qualquer mudança de código invalida
   as aprovações anteriores.
7. **Limite.** No máximo 3 rodadas em cada etapa. Se não convergir, pare e explique o impasse com
   opções.
8. **Entrega.** Relatório final: o que mudou e por quê, vereditos do reviewer e do QA, evidências,
   sugestões não bloqueantes e pendências. **Não faça commit nem push** sem autorização do Patrick.
