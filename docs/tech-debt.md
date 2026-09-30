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
- Observabilidade: o app não configura `logging` (sem `basicConfig` em `app/main.py`), então o logger
  raiz fica em WARNING e logs INFO, como o `áudio recusado: acima de N bytes` do handler, não
  aparecem no uvicorn. Configurar o nível/formato de log na inicialização.
- `pytest-randomly` está ativo: se algum teste novo depender de ordem, ele aparece como flaky.

## Resolvido (era alta prioridade)

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
