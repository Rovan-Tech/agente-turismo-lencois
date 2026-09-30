---
name: bugfix
description: Corrige um bug começando por um teste que reproduz a falha (regressão) e segue o fluxo completo (gate rápido, checklist de engenharia, code-reviewer, qa-tester). Use quando o Patrick reportar um defeito.
argument-hint: "<descrição do bug>"
disable-model-invocation: true
---

# /bugfix

Bug: **$ARGUMENTS**

1. **Reproduzir.** Entenda o comportamento esperado × obtido e escreva um **teste que falha** pelo
   motivo certo (unitário/integração; E2E se for no painel; `test_security.py` se for segurança).
   Rode e mostre a falha. Sem reprodução, não corrija: descreva o que falta saber.
2. **Pesquisar.** context7 para as bibliotecas envolvidas, se a causa envolver uma API.
3. **Corrigir** a causa raiz (não o sintoma), com a menor mudança possível, numa branch `fix/...`.
   O teste de regressão agora passa. Se a causa for uma falha de segurança, registre a ameaça no
   threat model da área (`docs/threat-models/`) ou abra um com `/threat-model`.
4. **Gate rápido e autoverificação**: `python3 scripts/quality_gate.py --fast` e `/checklist`
   sobre o diff; corrija todo `FALHA` antes de chamar os agents.
5. **Revisão** com o `code-reviewer` e **QA** com o `qa-tester`, exatamente como em `/feature`
   (briefing completo; checklist inteiro a cada rodada; qualquer `FALHA` = REPROVADO, volta ao
   reviewer; máximo 3 rodadas por etapa).
6. **Entrega**: causa raiz, correção, teste de regressão, vereditos com a contagem do checklist e
   pendências. Sem commit/push sem autorização.
