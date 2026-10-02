---
name: bugfix
description: Corrige um bug começando por um teste que reproduz a falha (regressão), com a menor mudança possível e gate rápido. Use quando o Patrick reportar um defeito.
argument-hint: "<descrição do bug>"
disable-model-invocation: true
---

# /bugfix

Bug: **$ARGUMENTS**

1. **Reproduzir:** escreva um teste que falha pelo motivo certo (unitário/integração; E2E se for no
   painel; `test_security.py` se for segurança) e mostre a falha. Sem reprodução, diga o que falta
   saber em vez de corrigir às cegas.
2. **Corrigir a causa raiz** com a menor mudança possível, numa branch `fix/...`. O teste passa.
   Falha de segurança: registre a ameaça no threat model da área.
3. **Gate rápido:** `python3 scripts/quality_gate.py --fast`.
4. **Revisão** (`/revisar`) só se o bug for de segurança, dados ou autenticação.
5. **Entrega:** causa raiz, correção, teste de regressão. Sem commit/push sem autorização.
