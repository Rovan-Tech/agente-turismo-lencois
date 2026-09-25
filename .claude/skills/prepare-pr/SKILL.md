---
name: prepare-pr
description: Deixa a branch atual pronta e abre o PR - sincroniza com a main (resolvendo conflito se houver), confere se os testes exigidos existem, roda /security-check e os mesmos checks do CI localmente (ruff, pytest, bandit, pip-audit no backend; prettier, tsc, vitest, playwright, build, npm audit no frontend), corrige o que falhar, sobe a branch e cria o PR com título e descrição do que foi feito. Use SOMENTE quando o usuário pedir explicitamente para abrir o PR — nunca por conta própria ao terminar uma tarefa, pois o usuário precisa testar antes.
---

# prepare-pr

Automatiza tudo entre "terminei de codar nesta branch" e "PR aberto, pronto para revisão". Só a
`main` é protegida (PR obrigatório); qualquer outra branch pode receber push livremente.

## Pré-condições

- **O usuário pediu explicitamente para abrir o PR** nesta conversa (ex: "abre o PR", "pode
  subir", `/prepare-pr`). Terminar uma tarefa não é motivo pra abrir PR sozinho — o usuário
  precisa testar a mudança antes. Sem pedido explícito, não execute este skill: avise que a
  mudança está pronta pra ser testada e que o PR sai quando ele mandar.
- A branch atual **não pode ser `main`**. Se estiver, pare e peça para o usuário indicar/criar
  a branch de trabalho — não invente um nome sem contexto.
- `origin` existe e `gh auth status` mostra acesso de escrita. Se não, pare e avise.

## Passo a passo

1. **Situação atual**: `git status`, `git branch --show-current`,
   `git log origin/main..HEAD --oneline`.

2. **Commitar pendências**: revise `git diff` e commite no estilo dos commits existentes
   (`git log`). Nada solto antes de seguir.

3. **Sincronizar com a `main`**:

   ```bash
   git fetch origin main
   git merge origin/main
   ```

   Conflito: resolva arquivo por arquivo entendendo a intenção dos dois lados — nunca escolha um
   lado às cegas. Se for ambíguo a ponto de arriscar lógica de negócio, pergunte.

4. **Conferir cobertura de testes**: para cada mudança em `git diff origin/main...HEAD`, existe o
   teste exigido pelo CLAUDE.md (pytest para lógica/endpoints no backend; Vitest para lógica/
   componentes e Playwright para tudo visível/interativo no frontend; teste de segurança para
   superfície de ataque)? Se faltar, escreva antes de seguir.

5. **Segurança**: rode o skill `/security-check`. Toda falha é corrigida com teste de regressão.

6. **Checks do CI localmente**, na mesma ordem de `.github/workflows/ci.yml`:

   ```bash
   # backend (working-directory: backend)
   pip install -r requirements.txt
   ruff check .
   ruff format --check .
   pytest
   bandit -r app -q
   pip-audit -r requirements.txt

   # frontend (working-directory: frontend)
   npm ci
   npm run format:check
   npm run check
   npm run test:unit
   npx playwright install --with-deps chromium
   npm run test:e2e
   npm run build
   npm audit --audit-level=high
   ```

   Só rode o job (`backend`/`frontend`) cuja pasta mudou, a menos que a mudança afete os dois
   (ex: contrato da API). Correção não trivial com dúvida sobre a intenção original → pergunte.
   Depois de qualquer correção, rode a sequência completa de novo.

7. **Subir a branch**: `git push -u origin $(git branch --show-current)`.

8. **Abrir o PR** a partir do que realmente mudou (`git log`/`git diff` contra `origin/main`):
   título curto no imperativo (< 70 caracteres), base `main`:

   ```bash
   gh pr create --base main --title "título aqui" --body "$(cat <<'EOF'
   ## Summary
   - ...

   ## Test plan
   - [x] backend: ruff, pytest, bandit, pip-audit
   - [x] frontend: prettier, tsc, vitest, playwright, build, npm audit

   ## Security
   - [x] bandit / pip-audit / npm audit / pentest local (/security-check)
   - achados e correções: ...
   EOF
   )"
   ```

9. **Reportar** a URL do PR pro usuário. Não faça merge nem approve.

## O que não fazer

- Não force-push para sincronizar — sempre merge.
- Não resolver conflito apagando um lado sem entender.
- Não pular checks, testes ou o `/security-check`.
- Não fazer merge/approve do próprio PR.
