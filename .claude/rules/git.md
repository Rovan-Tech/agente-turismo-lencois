# Git

- Commits em inglês, **Conventional Commits**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
  ✅ `fix: reject webhook with invalid signature` · ❌ `ajustes`
- Commits pequenos e atômicos (uma mudança lógica + seus testes).
- Branches `feat/...`, `fix/...`, `chore/...`. **Nunca commitar direto na `main`** (protegida: só PR
  com CI verde).
- **Nenhum commit ou push sem autorização explícita do Patrick.** `/prepare-pr` só quando ele pedir.
- Sem `--force`, `reset --hard`, `clean -fd` (o hook de guarda bloqueia).
- Nunca commitar credenciais, tokens ou IDs de serviços de terceiros.

## Manual V5 (ISO 9001 — higiene de Git, itens `GIT-1`..`GIT-3`)
- **Dois revisores antes do merge**: `code-reviewer` + `qa-tester` (ambos APROVADOS para o código
  atual) **e** a aprovação humana do PR. O corpo do PR traz o checklist preenchido.
- Nada sensível, temporário ou gerado no commit (`.env`, chaves, dumps, `__pycache__`,
  `.qa-artifacts`). Antes de abrir o PR: zero `print`/`console.log`/`debugger`, código comentado,
  comentário redundante e função fantasma (Anti-AI-slop; skill `/clean-code`).
- Código gerado por IA só entra se quem envia consegue explicar cada trecho.
