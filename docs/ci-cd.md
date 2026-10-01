# CI/CD

Como o repositório decide que um PR pode entrar na `main` e que um merge pode ir para produção.
O repositório é público, então os minutos do GitHub Actions não custam nada (requisito de custo zero).

## Visão geral

```
PR ──► changes ──┬─► pr-title        título no padrão Conventional Commits
                 ├─► secrets          gitleaks no histórico inteiro
                 ├─► workflows        actionlint + zizmor (só se .github/ ou scripts/ci/ mudou)
                 ├─► backend          quality_gate --full no PostgreSQL 17
                 ├─► migrations       alembic up, check, down, up num Postgres vazio
                 ├─► api-contract     fuzz do OpenAPI (schemathesis): nenhuma resposta 5xx
                 ├─► frontend         quality_gate --full + orçamento de bundle (size-limit)
                 ├─► docker           hadolint, build, Trivy, teste de fumaça do container, SBOM
                 └─► deps             dependency-review (dependência nova com CVE alta ou licença copyleft forte)
                          └──────────► ci-ok   único check obrigatório
PR ──► codeql (python, javascript-typescript, actions)      Semgrep (semgrep/ci)
main ─► CI ─► Deploy: build, proveniência SLSA, migração, Cloud Run, fumaça e rollback
03:17 UTC ─► Nightly: rescan, ZAP, k6, fuzz completo, mutação
```

O job `changes` classifica os arquivos do PR (`scripts/ci/changes.py`): um PR só de documentação não
sobe Postgres nem Docker. Fora de PR (push na `main`, merge queue) roda tudo. Job dispensado conta
como sucesso, e `ci-ok` só fica verde se nenhum job necessário falhou ou foi cancelado.

A classificação **falha aberta**: só PR de documentação pura (`docs/**` e `*.md`, exceto
`docs/checklist-engenharia.md`, `docs/tech-debt.md` e `.claude/`, que valem como código) pula jobs. Um caminho que nenhum grupo reconhece (hooks,
baselines, `.jscpd.json`, `Makefile`, arquivo novo na raiz) faz tudo rodar. O título do PR é
revalidado quando editado (`pull_request: edited`), o que reexecuta o pipeline inteiro.

## O que cada job garante

| Job | Garante | Reproduzir localmente |
| --- | --- | --- |
| `pr-title` | título `tipo(escopo): descrição`, que vira a mensagem do squash | `python3 scripts/ci/pr_title.py "feat: x"` |
| `secrets` | nenhum segredo no histórico (`.gitleaks.toml` libera só exemplos de skills de terceiros) | `docker run --rm -v "$PWD:/repo:ro" zricethezav/gitleaks git /repo --config /repo/.gitleaks.toml` |
| `workflows` | sintaxe e segurança dos workflows (permissões, injeção, ações sem SHA) | `actionlint` e `zizmor --config .github/zizmor.yml .github/workflows` |
| `backend` | formatação, ruff, mypy, pytest com cobertura (linhas alteradas), vulture, bandit, pip-audit, **em PostgreSQL** | `TEST_DATABASE_URL=postgresql+asyncpg://… python scripts/quality_gate.py --full --scope backend` |
| `migrations` | cada migration sobe, bate com o modelo e desce | `DATABASE_URL=… scripts/ci/check_migrations.sh` |
| `api-contract` | o fuzz não provoca 5xx, respostas dentro do schema e do content-type | `scripts/ci/start_api.sh && scripts/ci/fuzz_api.sh "$API_URL"` |
| `frontend` | prettier, tipos, Vitest com cobertura, build, Playwright (inclui **acessibilidade WCAG 2.2 AA**, `a11y.spec.ts`), npm audit, orçamento de bundle | `python scripts/quality_gate.py --full --scope frontend && npm run size` |
| `docker` | Dockerfile sem aviso de nível warning ou acima (hadolint), imagem sem CVE alta/crítica com correção (Trivy), sem segredo, container responde ao teste de fumaça, SBOM CycloneDX (artefato). O deploy reconstrói a imagem a partir do mesmo commit; ela não é a mesma escaneada, mas o nightly a reescaneia | os passos estão no `ci.yml` |
| `deps` | dependência nova sem CVE alta e sem licença AGPL, GPL-3.0 ou SSPL | só no PR (usa o grafo de dependências do GitHub) |
| `codeql` | análise estática de fluxo de dados (injeção, XSS, SSRF) | roda no GitHub; resultado em Security > Code scanning |

A suíte do backend roda em PostgreSQL via `TEST_DATABASE_URL` (o `conftest.py` cai em SQLite em
memória quando a variável não existe, que é o caso do desenvolvimento local).

## Noturno (`nightly.yml`)

Também sob demanda em Actions > Nightly > Run workflow. Falha avisa o dono do repositório por e-mail.

| Job | O que faz | Reprova quando |
| --- | --- | --- |
| `rescan` | pip-audit, npm audit e Trivy na imagem | CVE nova (sem o código mudar) |
| `dast` | OWASP ZAP contra a API no ar a partir do OpenAPI | alerta de nível FAIL (avisos só no relatório) |
| `load` | k6, 30 req/s por 30 s | erro > 1% ou p95 > 500 ms |
| `fuzz-full` | schemathesis com todos os checks | nunca (informativo; ver TD-C1) |
| `mutation` | mutmut em `tour_matcher` e na verificação HMAC | pontuação < 85% (hoje 88%) |

## Deploy (`deploy.yml`)

Só dispara depois do CI verde num push na `main` (ou manualmente). Ordem: build, push, atestado de
proveniência SLSA (`attest-build-provenance`), migração e seed do banco, deploy no Cloud Run,
`update-traffic --to-latest`, **teste de fumaça com rollback automático**, frontend no Cloudflare.

- A revisão anterior vem de `scripts/ci/previous_revision.sh`: no primeiro deploy (serviço
  inexistente) só avisa; qualquer outro erro do `gcloud` para o deploy antes de mexer no tráfego.
- O teste de fumaça (`scripts/ci/verify_deploy.sh`) tenta 6 vezes (tolera cold start). Se falhar,
  devolve 100% do tráfego à revisão que atendia antes e o job falha; o frontend não é publicado.
- `--to-latest` é necessário porque, depois de um rollback, o Cloud Run mantém o tráfego fixo na
  revisão antiga e os deploys seguintes deixariam de recebê-lo.
- **A migração roda antes do deploy.** Se houver rollback, o banco já está no schema novo: migration
  que quebra a versão anterior (renomear ou apagar coluna) exige duas etapas (adicionar, depois
  remover num deploy seguinte).

## Branch protection recomendada (configuração do repositório, não do código)

Hoje a proteção da `main` exige só `clickup-link`, e o ruleset `semgrep-required` exige `semgrep/ci`:
os jobs do `CI` (testes, segurança, imagem) não bloqueiam o merge. Recomendado, num ruleset:

- checks obrigatórios: `ci-ok`, `semgrep/ci`, `clickup-link` e `codeql (python)`,
  `codeql (javascript-typescript)`, `codeql (actions)`;
- exigir branch atualizada (`strict`) e proibir push direto e force push;
- em Settings > Code security: secret scanning, push protection e Dependabot security updates.

## Um CI vermelho fecha o PR (`pr-feedback-clickup.yml`)

Quando o workflow `CI` (ou o Semgrep) reprova num PR com link do ClickUp, o `pr-feedback-clickup`
muda a tarefa para "PR reprovado", comenta e **fecha o PR**; é preciso abrir outro. Vale para qualquer
job vermelho, inclusive instabilidade de rede (banco do Trivy, pull de imagem). **Exceção:** se só o
`pr-title` falhou, ele apenas comenta no PR; edite o título e o CI roda de novo sozinho.

## Mantendo o pipeline

- **Ações** estão fixadas por SHA de commit (com a versão no comentário) e **imagens Docker por
  digest**. O Dependabot (`.github/dependabot.yml`, semanal e agrupado) propõe as atualizações de
  ações, pip, npm e do Dockerfile. Os digests de `ci.yml` e `nightly.yml` (gitleaks, actionlint,
  hadolint, Trivy, ZAP, k6, Postgres e o container do Semgrep) são atualizados à mão: `docker pull <imagem>` e copie o
  `RepoDigest`.
- Nada de `${{ }}` dentro de `run:`; valores não confiáveis (título do PR, branch) vão por `env`.
- Ferramentas só do CI ficam em `scripts/ci/requirements-tools.txt` e `requirements-mutation.txt`
  (o Dependabot as acompanha), fora da imagem de produção. `backend/requirements.txt` tem só o que roda em produção; as
  ferramentas de desenvolvimento ficam em `requirements-dev.txt`.
- Os testes de `scripts/ci/` precisam de `bash`, `git`, `curl` e `jq` no PATH (todos presentes no
  `ubuntu-latest`).
- Os scripts de `scripts/ci/` têm testes em `backend/tests/tooling/test_ci_*.py` (fixtures no
  `conftest.py` da pasta). Só `start_api.sh` não tem teste próprio: é exercido pelos jobs que o usam.

## Quando um job falha

- **`backend` ou `migrations` só falham no CI**: reproduza com Postgres (`docker run -p 5432:5432
  -e POSTGRES_PASSWORD=postgres postgres:17`) e `TEST_DATABASE_URL`; SQLite perdoa coisas que o
  Postgres não perdoa.
- **`docker` reprova no Trivy**: a CVE tem correção publicada (`--ignore-unfixed` ignora só as que
  ainda não têm). Atualize a dependência ou a base; o Dockerfile já aplica `apt-get upgrade`. Não use
  `.trivyignore` sem o motivo e o prazo.
- **`api-contract` reprova**: o fuzz imprime o `curl` que reproduz e a semente (`--seed`).
- **`frontend` reprova em acessibilidade**: a falha lista a regra do axe e o seletor do elemento.
- **Teste de mutação cai abaixo do piso**: `mutmut results` lista os sobreviventes e
  `mutmut show <nome>` mostra a mudança que os testes não perceberam.
