# ADR-0002: Pipeline de CI/CD em camadas (portão de PR, noturno e deploy com rollback)

- **Status:** Aprovado (pelo Patrick, 2026-09-30)
- **Data:** 2026-09-30
- **Autores:** Patrick / Claude Code
- **Checklist afetado:** `SEC-1`, `SEC-4`, `SEC-5`, `INF-1`, `INF-2`, `INF-3`, `INF-5`, `TEST-2`, `TEST-3`, `FE-5`, `FE-6`, `GATE-1`

## Contexto

O CI atual tinha dois jobs (`backend` e `frontend`, ambos `quality_gate.py --full`), mais Semgrep e as
verificações de ClickUp. Não havia teste em PostgreSQL (a suíte rodava só em SQLite, e a produção é
Postgres), nem validação das migrations, da imagem Docker, de segredos no histórico, dos próprios
workflows, de acessibilidade, de peso do bundle ou de contrato da API. O deploy publicava sem conferir
se a revisão nova respondia. A proteção da `main` exige só o check `clickup-link` (e o ruleset `semgrep-required` exige
`semgrep/ci`): o CI de testes e segurança não bloqueia o merge.
Restrições: **custo zero** (o repositório é público, então os minutos do Actions são grátis) e nada de
serviço externo pago. Diversos itens do checklist (`SEC-1`, `SEC-5`, `INF-2`, `INF-3`, `FE-5`,
`TEST-2`, `TEST-3`) estavam em ⏳ à espera dessa infraestrutura (`docs/tech-debt.md`).

## Opções avaliadas

1. **Manter o CI atual.** Custo zero, nada a manter. Mas o PR continua entrando sem teste em Postgres,
   sem varredura de imagem, segredo ou contrato, e o deploy sem rollback.
2. **Pipeline em camadas com ferramentas de código aberto rodando no GitHub Actions (escolhida).**
   Portão do PR (rápido, determinístico), noturno (lento ou que detecta CVE nova sem mudança de código)
   e deploy com teste de fumaça e rollback. Ferramentas: gitleaks, actionlint, zizmor, hadolint, Trivy,
   CodeQL, dependency-review, schemathesis, axe, size-limit, OWASP ZAP, k6 e mutmut; Dependabot e
   CycloneDX. Tudo gratuito em repositório público; ações fixadas por SHA e imagens por digest.
3. **Serviços SaaS (SonarCloud, Snyk, Codecov, Datadog).** Menos manutenção e bons painéis, mas pagos
   ou limitados, enviam código e dependências a terceiros e quebram o requisito de custo zero.
4. **Só endurecer o que existe (permissões, pins), sem novos testes.** Barato, mas não responde ao
   pedido de rodar "todos os tipos de teste e segurança" antes de aceitar um PR.

## Decisão

Adotar a opção 2, em três camadas: o **portão de PR** (`ci.yml`, com `ci-ok` como único check
obrigatório; `codeql.yml`; `semgrep.yml`), o **noturno** (`nightly.yml`) e o **deploy** com
proveniência SLSA, teste de fumaça e rollback automático (`deploy.yml`). A descrição de cada job está em
`docs/ci-cd.md`. A suíte do backend passa a rodar em PostgreSQL 17, e a imagem de produção deixa de levar
ferramentas de desenvolvimento (`requirements.txt` só com o que roda).

Decisões dentro da decisão:

- **Fuzz de contrato no PR só com os checks de robustez** (nenhum 5xx, resposta dentro do schema). Os
  checks de documentação do contrato rodam no noturno e estão em `TD-C1`.
- **Stryker (mutação do frontend) descartado por ora**: o Stryker 10 não aplica as mutações com
  Vitest 5 e Vite 8 (placar falso de 13%, confirmado quebrando o código à mão). `TD-T1` fica aberto
  para o frontend; o backend usa mutmut (piso de 85%, hoje 88%).
- **Checkov não se aplica**: o repositório não tem IaC; zizmor e actionlint cobrem os workflows.
- **Cosign (assinatura de imagem) fica fora**: a proveniência SLSA do GitHub cobre a origem; `TD-I2`.
- **Mudar a proteção da `main`** (exigir `ci-ok`, CodeQL e Semgrep; secret scanning; push protection)
  é configuração do repositório, não do código, e depende da sua aprovação.

## Consequências positivas

- Todo PR passa por: título padronizado, segredos, workflows, gate completo em Postgres, migrations
  reversíveis, fuzz da API, acessibilidade WCAG 2.2 AA, orçamento de bundle, imagem (Trivy), SBOM e
  dependências novas, num único check (`ci-ok`).
- PR só de documentação não gasta minutos com Postgres e Docker; qualquer arquivo não reconhecido faz
  tudo rodar (falha aberta).
- CVE nova é detectada à noite sem depender de alguém mexer no código; DAST e carga rodam sem staging.
- O deploy volta sozinho para a revisão anterior se a nova não responder.
- Fecha, total ou parcialmente, `TD-A1`, `TD-A4`, `TD-F1`, `TD-I2`, `TD-I3`, `TD-I4`, `TD-T1`, `TD-T2`.

## Riscos e trade-offs

- **Mais minutos e mais coisa para manter.** Mitigação: repositório público (grátis), jobs por
  caminho, Dependabot para ações e ferramentas; os digests das imagens Docker dos workflows são
  atualizados à mão (`docs/ci-cd.md`).
- **Falso positivo trava um PR.** Mitigação: cada exceção é restrita e comentada (`.gitleaks.toml`
  só para exemplos de skills de terceiros, `.github/zizmor.yml`, e `DL3008` no `.hadolint.yaml`, que vale
  para o Dockerfile inteiro porque fixar a versão de cada pacote apt quebra o build; o Trivy cobre).
- **O deploy não pode ser testado fora do GCP.** Mitigação: o script de verificação tem testes com
  `gcloud` falso; o primeiro deploy real deve ser acompanhado.
- **A migração roda antes do deploy**; se houver rollback, o banco já está no schema novo. Migration que
  quebra a versão anterior exige duas etapas (documentado em `docs/ci-cd.md`).
- **CI vermelho fecha o PR.** O `pr-feedback-clickup.yml` (anterior a esta decisão) fecha o PR e muda a
  tarefa do ClickUp quando o workflow `CI` reprova. Com mais jobs dependentes de rede, uma instabilidade
  passageira passa a custar um PR novo. **Decidido pelo Patrick:** quando só o `pr-title` falha, o
  workflow apenas comenta no PR (o `edited` revalida) e não fecha; as demais falhas continuam fechando.
- **O noturno falha sem ninguém ter mexido no código** (CVE nova). É o objetivo, mas exige que alguém
  leia o e-mail.

## Plano de adoção e reversão

- Esta entrega: workflows, scripts em `scripts/ci/` (com 90+ testes em
  `backend/tests/tooling/test_ci_*.py`), configs, documentação e dívida atualizada. Os scripts, o
  gate, o fuzz, o k6, o size-limit, o axe, o gitleaks e o mutmut foram executados localmente com os mesmos
  comandos do CI e provados reprovando um defeito injetado. O que só roda no GitHub ou no GCP (deploy,
  CodeQL, dependency-review, ZAP no runner) não pôde ser provado fora deles: a primeira execução real
  é parte da adoção.
- Depois do merge: acompanhar a primeira execução real no GitHub, então ajustar a proteção da `main`.
- Reversão: reverter o PR devolve o `ci.yml` anterior (`backend` e `frontend`). Cada workflow novo é um
  arquivo independente e pode ser apagado sem afetar os demais.
