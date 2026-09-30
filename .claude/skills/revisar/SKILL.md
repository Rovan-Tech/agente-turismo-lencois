---
name: revisar
description: Roda só o code-reviewer sobre o diff atual (sem QA), que preenche o checklist de engenharia inteiro. Use para uma segunda opinião rápida antes de seguir o fluxo completo.
disable-model-invocation: true
---

# /revisar

1. Levante o contexto: `git status`, `git diff --stat $(git merge-base HEAD origin/main)` e os
   arquivos não rastreados. Se não houver mudanças, diga isso e pare.
2. Invoque o subagent `code-reviewer` com o briefing completo: objetivo da mudança (deduza do diff e
   dos commits; pergunte se não der), critérios de aceite, lista de arquivos alterados (declare o
   escopo: o restante da branch é de outra entrega), branch base `origin/main`, como rodar testes
   (`python3 scripts/quality_gate.py --fast`) e, se já houve uma revisão nesta sessão, o que mudou
   desde o último relatório.
3. Apresente o relatório do subagent **inteiro, incluindo a seção `Checklist:`**, sem editar nada.
   Se REPROVADO, liste os itens `FALHA`, BLOQUEANTES e IMPORTANTES e pergunte se deve corrigir (a
   correção segue o fluxo de `/feature`).
