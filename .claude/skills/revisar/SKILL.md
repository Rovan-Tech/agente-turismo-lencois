---
name: revisar
description: Roda uma passada do code-reviewer sobre o diff atual. Use em mudança de risco ou para uma segunda opinião.
disable-model-invocation: true
---

# /revisar

1. `git status` e `git diff --stat $(git merge-base HEAD origin/main)`. Sem mudanças, diga isso e pare.
2. Invoque o subagent `code-reviewer` com um briefing curto: objetivo (deduza do diff e dos commits),
   arquivos alterados (o escopo), branch base `origin/main`.
3. Apresente o relatório e, se REPROVADO, liste os BLOQUEANTES e IMPORTANTES e pergunte se deve corrigir.
