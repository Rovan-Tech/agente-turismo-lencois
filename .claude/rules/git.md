# Git

- Commits em inglês, **Conventional Commits**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
  ✅ `fix: reject webhook with invalid signature` · ❌ `ajustes`
- Commits pequenos e atômicos (uma mudança lógica + seus testes).
- Branches `feat/...`, `fix/...`, `chore/...`. **Nunca commitar direto na `main`** (protegida: só PR
  com CI verde).
- **Nenhum commit ou push sem autorização explícita do Patrick.** `/prepare-pr` só quando ele pedir.
- Sem `--force`, `reset --hard`, `clean -fd` (o hook de guarda bloqueia).
- Nunca commitar credenciais, tokens ou IDs de serviços de terceiros.
