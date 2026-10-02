---
name: prepare-pr
description: Deixa a branch atual pronta e abre o PR - sincroniza com a main (resolvendo conflito se houver), confere se os testes exigidos existem, roda o gate de qualidade completo (`scripts/quality_gate.py --full`, a mesma fonte do CI), corrige o que falhar, sobe a branch e cria o PR com título e descrição do que foi feito. Use SOMENTE quando o usuário pedir explicitamente para abrir o PR — nunca por conta própria ao terminar uma tarefa, pois o usuário precisa testar antes.
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

5. **Segurança**: o CI já roda CodeQL, Semgrep, gitleaks e auditoria de dependências. Rode
   `/security-check` só se a mudança mexe em autenticação, webhook ou dado pessoal.

6. **Gate:** rode o gate completo, a mesma fonte do CI, depois de conferir o básico do
   `/clean-code` (zero `print`/`console.log`/`debugger`, código comentado e comentário redundante):

   ```bash
   python3 scripts/quality_gate.py --full
   ```

   Correção não trivial com dúvida sobre a intenção original → pergunte. Se a mudança for de risco
   (auth, webhook, dado pessoal, LLM, migração), rode `/revisar` antes de abrir o PR.

7. **Subir a branch**: `git push -u origin $(git branch --show-current)`.

8. **Abrir o PR** a partir do que realmente mudou (`git log`/`git diff` contra `origin/main`):
   título curto no imperativo (< 70 caracteres), base `main`:

   ```bash
   gh pr create --base main --title "título aqui" --body "$(cat <<'EOF'
   ## Summary
   - ...

   ## Test plan
   - [x] `python3 scripts/quality_gate.py --full` verde
   - [x] revisão (`/revisar`), se a mudança era de risco

   ## Documentos
   - ADR: docs/adr/NNNN-… (se houve) · Threat model: docs/threat-models/… (se houve)

   ## Security
   - [x] CI (CodeQL, Semgrep, gitleaks, auditorias); `/security-check` se aplicável
   - achados e correções: ...
   EOF
   )"
   ```

9. **Reportar** a URL do PR pro usuário. Não faça merge nem approve.

## O que não fazer

- Não force-push para sincronizar — sempre merge.
- Não resolver conflito apagando um lado sem entender.
- Não pular checks nem testes.
- Não fazer merge/approve do próprio PR.
