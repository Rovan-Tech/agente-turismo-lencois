# Dívida técnica (linha de base)

Medida em 2026-09-29 com `python scripts/quality_gate.py --full` e as ferramentas do `pyproject.toml`
na **árvore inteira**. O gate só falha em **linhas novas ou alteradas**; nada abaixo foi corrigido
por este setup. Ao mexer num arquivo listado, resolva os itens das linhas que você tocar.

**Atualizado em 2026-09-29** (feature do CRUD de passeios): a cobertura de testes subiu bastante
porque essa mudança fechou de propósito as lacunas que o setup original tinha deixado (era
justamente o pedido do Patrick — teste unitário de todos os arquivos, não só do que fosse novo).
Também corrigimos de raiz uma causa comum de subcobertura: o `coverage.py` não rastreava a linha
seguinte a um `await` que passa pelo `greenlet` do SQLAlchemy async, então vários arquivos
apareciam com menos cobertura do que realmente tinham — ver `[tool.coverage.run]` em
`backend/pyproject.toml` (`concurrency = ["greenlet", "thread"]`).

## Resumo

| Tipo             | Ferramenta                    | Achados hoje                                                               | Prioridade |
| ---------------- | ------------------------------ | -------------------------------------------------------------------------- | ---------- |
| Testes/cobertura | pytest-cov (linhas+ramos)     | backend **95%**; frontend **95%** (linhas)                                | Baixa      |
| Tipos            | mypy `--strict`               | 15 erros em 9 arquivos                                                     | Média      |
| Documentação     | ruff `D`                      | 59 (D100 ×15, D101 ×10, D102, D103 ×25, D104 ×6, D107, D415)               | Média      |
| Segurança        | ruff `S105`                   | 4 (1 em `app/core/config.py`, 3 em `tests/`)                               | Média      |
| Tipos/estilo     | ruff `ANN`, `PLR0913`         | 3                                                                          | Baixa      |
| Limites          | `check_limits.py`             | 3 funções > 40 linhas                                                      | Baixa      |
| Código morto     | vulture                       | 0 (o `cls` do validator está em `ignore_names`)                            | —          |
| Duplicação       | jscpd (6+ linhas, 20+ tokens) | 7 clones: `seed.py` ×3, `test_webhook.py`, `ConversationsPage.test.tsx` ×3 | Baixa      |
| Dependências     | pip-audit / npm audit         | 0                                                                          | —          |

## Alta prioridade

- **Ferramentas de dev na imagem de produção**: `pytest`, `ruff`, `bandit`, `pip-audit` e `aiosqlite`
  continuam em `backend/requirements.txt`, que o `Dockerfile` instala. Ainda não foi resolvido por
  nenhuma mudança até agora. Mover para `requirements-dev.txt` (o arquivo já existe; falta remover
  de `requirements.txt`) reduz a imagem e a superfície de ataque. Exige ajustar o `deploy.yml` se
  ele usar `pytest` no build — ver `docs/deploy.md` antes de mexer.

## Decisões de produto pendentes (CRUD de passeios)

- **Mensagens de erro do Pydantic em inglês no painel**: `frontend/src/lib/api.ts`
  (`extractErrorMessage`) usa `detail[0].msg` direto da resposta 422, que sai em inglês (ex.
  "Input should be a finite number"). Sem tradução hoje; confirmar com o Patrick se vale a pena
  traduzir (mapeamento de mensagens comuns) ou se o painel é uso interno o bastante pra não
  importar.
- **Teto de `duracao_horas` (`le=24` em `backend/app/api/tours.py`)**: bloqueia travessias de vários
  dias, se algum dia isso entrar no catálogo. Confirmar com o Patrick se 24h é o teto certo. Se
  mudar, ajustar também o `max` do campo "Duração (horas)" em `frontend/src/components/TourForm.tsx`
  (hoje espelha o backend).

## Média prioridade

- **mypy strict (15)**: `dict` sem parâmetros de tipo em `api/conversations.py`, `api/webhook.py`,
  `main.py:health`, `db/session.py`, `models/tour.py`, `services/tour_matcher.py`
  (`dict[str, Any]`/`TypedDict`); `whatsapp_client.py:28` retorna `Any`; `transcription.py` sem
  retorno tipado e sem stubs do `faster_whisper`; `tests/test_webhook.py` (reexport de
  `whatsapp_client`, mesmo problema evitado em `tests/test_message_handler.py` importando o
  módulo direto). `app/api/tours.py` e `app/services/tour_catalog.py` já usam `dict[str, object]`
  em vez de `dict` — usar como referência ao tocar os arquivos acima. Nos testes o mypy tolera
  funções e chamadas de helpers sem tipos (override `tests.*` no `pyproject.toml`).
- **Docstrings** (`D1xx`): quase todos os módulos, classes e funções públicas de `app/` (tests já
  ignoram `D`). Escrever em pt-BR, estilo Google. `app/api/tours.py` e
  `app/services/tour_catalog.py` já estão documentados.
- **S105**: `app/core/config.py:38` (`whatsapp_verify_token` com valor literal por padrão — confirmar
  que o padrão não é um segredo utilizável em produção) e 3 tokens de teste em `tests/conftest.py`
  e `tests/test_security.py` (fixtures; marcar como constantes de teste). Os testes novos
  (`test_deps.py`, `test_whatsapp_client.py`) já evitam o padrão que dispara S105/S106 — ver como
  fizeram (`monkeypatch.setattr(settings, "campo", valor)` em vez de passar o campo como
  `kwarg`/nome de variável contendo "token"/"password").

## Baixa prioridade

- `ANN202`/`ANN204` (1 cada), `PLR0913` (a de `process_incoming_message` foi resolvida com o objeto `IncomingMessage`).
- Duplicação: as três entradas de `seed.py` e os setups repetidos de `test_webhook.py` e
  `ConversationsPage.test.tsx` viram helper/fixture ao serem tocados. (Os testes novos já usam
  esse padrão: `backend/tests/test_tours.py` tem `_persist`/`_valid_payload`,
  `frontend/tests/unit/fixtures.ts` compartilha `SAMPLE_TOUR`/`fillTourFormRequiredFields`.)
- Funções acima de 40 linhas: `alembic/versions/0001_initial_schema.py:upgrade` (44, gerada), `tests/conftest.py:sample_tours` (45).
- Áudio: o teto é só em bytes (`MAX_AUDIO_BYTES`, 5 MiB ≈ 20–30 min de Opus do WhatsApp); um limite
  por duração (ler o cabeçalho Ogg antes do Whisper) segue pendente.
- Webhook: só a **idempotência** foi feita (índice único em `messages.whatsapp_message_id`). O
  processamento continua dentro da requisição de propósito: no Cloud Run com cobrança por
  requisição (`--min-instances=0`, sem `--no-cpu-throttling`) o trabalho depois do 200 é
  "background activity" sem CPU garantida e pode se perder. Responder 200 na hora exige
  `--no-cpu-throttling` (cobrança por instância, pode sair do free tier) ou fila/Cloud Tasks.
  A resposta é enviada antes do `commit`: se o envio falha, o reenvio da Meta reprocessa; no caso
  raro inverso (envio ok e `commit` falha), o reenvio responde o turista duas vezes.
- Resolver uma conversa enquanto o bot ainda responde nela (a chamada ao Groq leva segundos):
  `_record_reply` grava o status decidido pela IA sobre o objeto carregado antes e pode
  sobrescrever o `resolvida` recém-gravado; se o valor for igual, a mensagem do turista fica dentro
  de uma conversa resolvida. A próxima mensagem abre outra conversa (o telefone aparece duas vezes).
  Sem perda de dados; endurecer com `refresh`/`UPDATE ... WHERE status != 'resolvida'`.
- Painel (lista): a busca é feita no navegador sobre o telefone e a **prévia da última mensagem**
  (a API trunca em 200 caracteres). Achar uma palavra dita no meio da conversa exige um parâmetro
  de busca na API. O indicativo "Assistente de IA respondendo agora" da barra lateral é fixo: não
  reflete o estado real do bot.
- Lista de conversas: a prévia da última mensagem usa `row_number() OVER (PARTITION BY ...)`, que
  percorre todas as mensagens a cada GET (só há índice em `conversation_id`), e a lista não tem
  paginação. Serve ao volume do portfólio; com muito histórico, trocar por `LATERAL ... LIMIT 1`
  (Postgres) ou criar o índice `(conversation_id, created_at)` e paginar.
- Painel: se a API de conversas falhar ou devolver um contrato quebrado (validado por Zod), a lista
  mostra "Nenhuma conversa encontrada" em vez de um estado de erro (`ConversationsPage` faz
  `data ?? []`). O `vite dev` também loga `GET /favicon.ico` 404 (não há ícone em `index.html`).
- Webhook: uma mensagem assinada de tamanho enorme é aceita e gravada inteira no banco; só o texto
  enviado ao Groq é limitado a 1000 caracteres. O teto de tamanho do corpo do webhook depende do
  limite de taxa/volume (TD-A3).
- Webhook: um payload assinado e bem-formado como JSON, mas com estrutura inesperada
  (`{"entry": "x"}`, `{"entry": [null]}`, `messages: ["x"]`), devolve 500 em `_extract_messages`, que
  assume dict e lista. Só a Meta assinante consegue disparar (achado do QA, fora deste diff).
- Observabilidade: o app não configura `logging` (sem `basicConfig` em `app/main.py`), então o logger
  raiz fica em WARNING e logs INFO, como o `áudio recusado: acima de N bytes` do handler, não
  aparecem no uvicorn. Configurar o nível/formato de log na inicialização.
- `pytest-randomly` está ativo: se algum teste novo depender de ordem, ele aparece como flaky.

## Conformidade com o Manual V5 (medida em 2026-09-30)

Lacunas entre o código/infra atuais e o `docs/checklist-engenharia.md` (ADR-0001). Os itens ⏳ do
checklist apontam para cá. As regras valem para código novo ou alterado; estes itens são o legado e a
infraestrutura que ainda faltam. Ao tocar uma área, resolva os itens dela.

| ID | Item do checklist | Lacuna | Prioridade |
| --- | --- | --- | --- |
| TD-A1 | `SEC-1` | gitleaks roda no CI (job `secrets`, histórico inteiro). Falta o pre-commit (hoje só o padrão do hook `post_edit_quality`) | Baixa |
| TD-A2 | `FE-1` | `zod` instalado; as respostas de **conversas** (lista, detalhe e troca de status) já são validadas em `lib/api.ts`. Faltam os passeios (`listTours`, `createTour`, `updateTour`, `deleteTour`), que ainda usam o caminho sem schema | Média |
| TD-A3 | `SEC-3` | sem limite de taxa no webhook e na API do painel (ex.: `slowapi`) | Alta |
| TD-A4 | `SEC-5`, `INF-2` | SBOM CycloneDX da imagem do backend sai no CI (job `docker`, artefato `sbom-backend`). Falta o SBOM do frontend (`@cyclonedx/cyclonedx-npm`) | Baixa |
| TD-A5 | `DATA-3` | sem tabela de auditoria append-only com hash chain; mutações (`status` da conversa, CRUD de passeios) não registram quem/quando/antes/depois | Alta |
| TD-A6 | `FE-3` | o painel está atrás do Cloudflare Access (feito em 2026-10-01) e o backend valida o JWT do Access (ADR-0006), mas o deploy ainda roda em `PANEL_AUTH_MODE=token`: o bundle segue com o token fixo (`VITE_API_TOKEN`) até a variável passar para `both` e `access` (ver `docs/deploy.md`). Ao chegar em `access`, remover `DASHBOARD_API_TOKEN` do deploy e fechar esta dívida | Média |
| TD-G1 | `GIT-1` | pre-commit sem `check-added-large-files` (500 KB) | Baixa |
| TD-M5 | `PY-4` | sem handler global RFC 7807; erros saem como `{"detail": ...}` do FastAPI | Média |
| TD-M6 | `PY-5` | sem biblioteca de retry/circuit breaker (`tenacity`); jitter e breaker não padronizados nas chamadas ao Groq e ao WhatsApp | Média |
| TD-M7 | `FE-4` | não existe `frontend/public/_headers` com CSP; nonce dinâmico exigiria Worker/SSR | Média |
| TD-M8 | `PY-3` | `StatusUpdate` (`api/conversations.py`) e `TourFields` (`api/tours.py`) sem `strict=True` nem `extra="forbid"` | Média |
| TD-F1 | `FE-5` | `size-limit` roda no CI (JS 110 kB e CSS 8 kB gzip, `npm run size`). Faltam `React.lazy`/`Suspense` nas rotas | Baixa |
| TD-F2 | `FE-8` | Storybook não adotado (exige ADR) | Baixa |
| TD-F3 | `FE-2` | painel em `pages/components/lib`; migração para `features/` só quando reescrito | Baixa |
| TD-O1 | `OBS-1`, `OBS-2` | sem logs JSON com `correlation_id`/`trace_id`/`span_id`, sem filtro de PII, sem OpenTelemetry nem métricas RED/USE | Alta |
| TD-O2 | `OBS-4` | SLO/SLA/SLI e plano de recuperação de desastres (RPO/RTO < 15 min) não documentados; definir em `docs/slo.md` e `docs/deploy.md` (PITR do Neon, rollback do Cloud Run) | Média |
| TD-O3 | `OBS-3` | Chaos Engineering em staging inexistente (não há staging) | Baixa |
| TD-I1 | `INF-1` | `backend/Dockerfile` single-stage em `python:3.11-slim` (usuário já é não-root) | Média |
| TD-I2 | `INF-2` | Trivy (imagem e Dockerfile) no CI e proveniência SLSA no `deploy.yml`. Falta a assinatura Cosign | Baixa |
| TD-I3 | `INF-3` | workflows com `permissions` mínimas, ações por SHA, imagens por digest, actionlint e zizmor no CI. Checkov não se aplica (não há IaC no repositório) | Baixa |
| TD-I4 | `INF-5` | o deploy tem teste de fumaça e rollback automático para a revisão anterior. Faltam canary (divisão de tráfego) e flag de desligamento | Média |
| TD-I5 | `INF-1` | o Dependabot não propõe mais troca de versão do Python (ignora minor e major da imagem); o Python 3.11 sai de suporte de segurança em out/2027. Planejar a migração (faster-whisper, ctranslate2 e onnxruntime precisam ter pacote para a versão nova), junto com TD-I1 | Média |
| TD-T1 | `TEST-2` | mutmut noturno no backend (`tour_matcher` e HMAC; 88%, piso 85%). Mutation do frontend pendente: o Stryker 10 não aplica as mutações com Vitest 5 e Vite 8 (placar falso de 13%, confirmado à mão) | Baixa |
| TD-T2 | `TEST-3` | OWASP ZAP roda toda noite contra a API local do CI (sem staging). Falta rodar contra o ambiente publicado | Baixa |
| TD-C1 | `PY-3`, `DOC-1` | o contrato OpenAPI não declara os status que a API devolve (400, 403, 404, 409, 422), o cabeçalho `Allow` no 405 nem `securitySchemes` (por isso o check `ignored_auth` não funciona e o fuzz sempre vai autenticado). `POST`/`PUT /api/tours` aceitam campo extra e rejeitam `min_length` e texto só com espaços de formas que o schema não descreve (ver TD-M8). Achados do fuzz completo noturno (`fuzz-full`, resumo no painel da execução) | Média |
| TD-C2 | `SEC-3` | as respostas da API não trazem `X-Content-Type-Options: nosniff` nem `Cross-Origin-Resource-Policy`; achado do ZAP noturno | Média |
| TD-C3 | `TEST-2` | 15 mutantes sobrevivem em `app/services/tour_matcher.py` (`extract_criteria`, `filter_tours`): os testes não exigem esses comportamentos (o 16º sobrevivente do mutmut, em `app/core/security.py`, é equivalente: `"utf-8"` vira `"UTF-8"`) | Média |
| TD-N1 | `DATA-1` | o fluxo no n8n (ADR-0004) não deduplica pelo id da mensagem; a Meta reenvia o webhook e o turista pode receber a resposta duas vezes | Média |
| TD-N2 | `SEC-3` | o gatilho de WhatsApp do n8n compara a assinatura `X-Hub-Signature-256` com `!==` (não é tempo constante). Dependência de terceiro; reavaliar se o fluxo voltar ao backend | Baixa |
| TD-N4 | `AI-3` | o fluxo no n8n ignora áudio e envia o catálogo inteiro ao Gemini; o backend filtrava candidatos (`tour_matcher`) e transcrevia com faster-whisper | Média |
| TD-N5 | `SEC-6` | telefone e texto do turista ficam nas execuções do n8n Cloud sem política de retenção definida | Alta |
| TD-N6 | `SEC-7`, `TEST-1` | o workflow do n8n não tem teste automatizado; os testes de assinatura forjada e de injeção de prompt foram feitos à mão em 2026-10-01 (`docs/threat-models/2026-10-01-n8n-gemini-whatsapp.md`) | Média |
| TD-N7 | `SEC-1` | chave JSON da service account do Vertex no n8n (política da organização relaxada para criá-la; reativar e rotacionar) e token do usuário do sistema da Meta sem expiração, gerado com as permissões padrão (reduzir a `whatsapp_business_messaging`) | Alta |
| TD-N8 | `INF-4` | custo deixou de ser zero (plano do n8n Cloud e Gemini por token); falta alerta de orçamento no Google Cloud, assinar só o status `failed` no gatilho e revisar `INF-4`/`AI-3` e a regra de custo zero do `CLAUDE.md` depois da aprovação do ADR-0004 | Alta |
| TD-N9 | `DATA-1` | `get_or_create_open_conversation` faz SELECT e depois INSERT sem trava nem índice único parcial: duas primeiras mensagens do mesmo telefone quase simultâneas criam duas conversas abertas (medido: 5 conversas em 10 chamadas paralelas no Postgres). Vale para o webhook antigo e para o `POST /api/ingest/atendimentos`; sem perda de dado | Baixa |

**Fora da dívida (N/A por arquitetura, ADR-0001):** RLS (`DATA-4`, single-tenant), mTLS/service mesh
(`INF-6`, serviço único), Transactional Outbox (`PY-6`, sem mensageria). **Substituições permanentes
por custo/peso (ADR-0001):** SonarQube → bandit + Semgrep + ruff `S` (`SEC-4`); NeMo Guardrails/Llama
Guard → delimitação + limite + filtro + teste adversário (`AI-1`).

## Resolvido (era alta prioridade)

- ~~TD-N3: as conversas atendidas pelo n8n não chegavam ao painel~~: o ADR-0005 criou
  `POST /api/ingest/atendimentos` (token próprio, idempotente) e o expurgo de 90 dias das conversas.
  Vale para mensagens de **texto**; o áudio e o filtro de candidatos do catálogo seguem em TD-N4
  (etapas 2b e 2c, com ADR próprio cada uma).
- ~~Cobertura baixa em código crítico~~: `seed.py` (dados do catálogo validados, 0%→43% — falta só
  a função `seed()` em si, que grava no banco de verdade e não vale o esforço de mockar pra um
  script de uso único), `transcription.py` 0%→83% (a única lacuna real é `_get_model`, que
  instancia o `WhisperModel` de verdade — mockado nos testes por ser fronteira externa, como manda
  `testing.md`), `whatsapp_client.py` 26%→100%, `message_handler.py` 40%→100%. Frontend: 42%→95%
  — `ConversationDetailPage.tsx` 0%→100% (linhas), `App.tsx` 0%→100%, `lib/api.ts` 22%→94%.
  `groq_client.py` continua em 72% (não foi tocado por esta mudança; ainda é o serviço do bot
  menos coberto).

## Pontos de atenção do setup (não são dívida do código)

- Lockfile do backend: `requirements.txt` fixa versões diretas, mas não há lock com hashes.
  `numpy` (transitivo via `faster-whisper`→`onnxruntime`/`ctranslate2`) passou a ser pinado
  explicitamente (`numpy==2.1.3`) depois que uma instalação limpa resolveu uma versão cujo stub
  usa sintaxe (`type X = ...`) que o mypy só aceita com `python_version >= 3.12` — quebrava
  `mypy --strict` (configurado pra `3.11`) com um erro de sintaxe, não um erro de tipo de verdade.
  Reproduz em qualquer máquina sem lockfile de hashes; vale considerar um lock completo
  (`pip-compile`/`uv pip compile`) pra não depender de mais nenhum pin manual como esse.
- `.nvmrc` fixa Node 22; a máquina de desenvolvimento local está em Node 26 (gate e E2E passaram).
- `ruff==0.8.4` está antigo; subir a versão pode adicionar regras (rodar o gate ao atualizar).
- Frontend sem ESLint: a cobertura de regras vem de `tsc --strict`, Prettier e do verificador de
  tokens. Avaliar ESLint (`eslint-plugin-jsx-a11y`) para reforçar acessibilidade.
- Python 3.11 não está disponível nesta máquina de desenvolvimento (só 3.12); o venv do backend foi
  criado com 3.12. Não houve diferença de comportamento observada além do problema do `numpy`
  acima, mas se algo depender de sintaxe/semântica específica de 3.11 x 3.12, vale investigar
  primeiro se é ambiente antes de assumir bug de código.
