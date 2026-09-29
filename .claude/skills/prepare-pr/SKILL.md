---
name: prepare-pr
description: Deixa a branch atual pronta e abre o PR - sincroniza com a main (resolvendo conflito se houver), confere se os testes exigidos existem, roda /security-check e o gate de qualidade completo (`scripts/quality_gate.py --full`, a mesma fonte do CI), corrige o que falhar, sobe a branch e cria o PR com título e descrição do que foi feito. Use SOMENTE quando o usuário pedir explicitamente para abrir o PR — nunca por conta própria ao terminar uma tarefa, pois o usuário precisa testar antes.
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

6. **Fluxo de revisão e gate**: confirme que `code-reviewer` e `qa-tester` aprovaram o código
   atual (o hook `SubagentStop` registra o veredito) e rode o gate completo, a mesma fonte do CI:

   ```bash
   python3 scripts/quality_gate.py --full
   ```

   Ele cobre backend (formatação, ruff, mypy, pytest+cobertura, vulture, bandit, pip-audit) e
   frontend (prettier, tsc, vitest+cobertura, build, npm audit, E2E). Correção não trivial com
   dúvida sobre a intenção original → pergunte. Depois de qualquer correção, rode o gate de novo e
   volte ao `code-reviewer` (mudança de código invalida as aprovações).

7. **Subir a branch**: `git push -u origin $(git branch --show-current)`.

8. **Abrir o PR** a partir do que realmente mudou (`git log`/`git diff` contra `origin/main`):
   título curto no imperativo (< 70 caracteres), base `main`:

   ```bash
   gh pr create --base main --title "título aqui" --body "$(cat <<'EOF'
   ## Summary
   - ...

   ## Test plan
   - [x] `python3 scripts/quality_gate.py --full` verde
   - [x] code-reviewer e qa-tester APROVADOS

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
