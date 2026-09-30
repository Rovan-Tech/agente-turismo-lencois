---
name: feature
description: Implementa uma funcionalidade seguindo o fluxo obrigatório do projeto (entender, checklist de engenharia, ADR/STRIDE quando aplicável, pesquisar no context7, implementar com testes, gate rápido, code-reviewer, qa-tester, relatório final). Use quando o Patrick pedir uma funcionalidade nova ou uma mudança de comportamento.
argument-hint: "<descrição da funcionalidade>"
disable-model-invocation: true
---

# /feature

Tarefa: **$ARGUMENTS**

Execute o fluxo do `CLAUDE.md` (seção "Fluxo obrigatório") do começo ao fim, sem pular etapas.
Acompanhe cada etapa com a lista de tarefas. O padrão é o checklist `docs/checklist-engenharia.md`
(Manual V5): **não há exceção**, e qualquer `FALHA` de qualquer agente é `REPROVADO`.

1. **Entender.** Escreva os critérios de aceite (testáveis, um por linha). Se a tarefa for grande ou
   ambígua, apresente um plano curto e peça aprovação antes de codar.
2. **Checklist e processo pré-código.** Leia `docs/checklist-engenharia.md` e liste os itens que a
   tarefa aciona (e os `N/A` prováveis, com o motivo). Então:
   - mudança arquitetural (banco, biblioteca de infraestrutura, padrão de comunicação, provedor
     de LLM) → `/adr <título>` e **espere o Patrick aprovar** antes de codar (`GOV-1`);
   - funcionalidade crítica (endpoint, webhook, autenticação, dado pessoal, LLM) →
     `/threat-model <funcionalidade>`; cada mitigação entra no plano de testes (`GOV-2`, `SEC-7`).
3. **Pesquisar.** Para cada biblioteca envolvida, consulte o context7 (`resolve-library-id` →
   `query-docs`). Não confie na memória para APIs.
4. **Implementar com testes** (TDD quando viável: teste falhando → código → refatoração), seguindo
   `.claude/rules/`. Mudança visível no painel exige spec Playwright; superfície de ataque exige teste
   em `test_security.py`. Trabalhe numa branch `feat/...` (nunca na `main`).
5. **Gate rápido e autoverificação.** `python3 scripts/quality_gate.py --fast` até ficar verde, depois
   `/checklist` sobre o diff. Corrija todo item `FALHA` **antes** de chamar os agents. Nunca
   silencie erro nem afrouxe regra.
6. **Revisão.** Invoque o subagent `code-reviewer` com o briefing completo: objetivo, critérios de
   aceite, arquivos alterados e branch base (`origin/main`), caminhos do ADR/threat model, itens do
   checklist que você considera `N/A` (com o motivo, para ele contestar), como subir o app e rodar
   os testes e, a partir da 2ª rodada, o que mudou desde o último relatório. REPROVADO → corrija
   todos os itens `FALHA` e todos os BLOQUEANTES e IMPORTANTES e invoque de novo.
7. **QA.** Com a revisão aprovada, invoque `qa-tester` com o mesmo briefing. REPROVADO → transforme
   cada bug e cada `FALHA` num teste ou correção verificável e **volte ao passo 6**: qualquer
   mudança de código invalida as aprovações anteriores, e os dois agents refazem o checklist inteiro.
8. **Limite.** No máximo 3 rodadas em cada etapa. Se não convergir, pare e explique o impasse com
   opções. Nunca "resolva" o impasse editando o checklist, um limite ou um hook.
9. **Entrega.** Relatório final: o que mudou e por quê, vereditos do reviewer e do QA com a contagem
   do checklist (OK · N/A · FALHA) e a lista de `N/A` com justificativa, evidências, sugestões não
   bloqueantes e pendências (ADR aguardando aprovação, dívidas `TD-*`). **Não faça commit nem push**
   sem autorização do Patrick.
