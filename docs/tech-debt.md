# Dívida técnica (linha de base)

Medida em 2026-09-29 com `python scripts/quality_gate.py --full` e as ferramentas do `pyproject.toml`
na **árvore inteira**. O gate só falha em **linhas novas ou alteradas**; nada abaixo foi corrigido
por este setup. Ao mexer num arquivo listado, resolva os itens das linhas que você tocar.

## Resumo

| Tipo             | Ferramenta                    | Achados hoje                                                               | Prioridade |
| ---------------- | ----------------------------- | -------------------------------------------------------------------------- | ---------- |
| Testes/cobertura | pytest-cov (linhas+ramos)     | backend **78,09%**; frontend **42,42%** (linhas)                           | Alta       |
| Tipos            | mypy `--strict`               | 16 erros em 10 arquivos                                                    | Média      |
| Documentação     | ruff `D`                      | 62 (D100 ×17, D101 ×10, D102, D103 ×26, D104 ×6, D107, D415)               | Média      |
| Segurança        | ruff `S105`                   | 4 (1 em `app/core/config.py`, 3 em `tests/`)                               | Média      |
| Tipos/estilo     | ruff `ANN`, `PLR0913`         | 3                                                                          | Baixa      |
| Limites          | `check_limits.py`             | 3 funções > 40 linhas                                                      | Baixa      |
| Código morto     | vulture                       | 0 (o `cls` do validator está em `ignore_names`)                            | —          |
| Duplicação       | jscpd (6+ linhas, 20+ tokens) | 7 clones: `seed.py` ×3, `test_webhook.py`, `ConversationsPage.test.tsx` ×3 | Baixa      |
| Dependências     | pip-audit / npm audit         | 0                                                                          | —          |

## Alta prioridade

- **Cobertura baixa em código crítico** (baseline em `.coverage-baseline.json`; só pode subir):
  `seed.py` 0%, `transcription.py` 0%, `whatsapp_client.py` 26%, `message_handler.py` 40%,
  `groq_client.py` 72%. O fluxo ponta a ponta do bot (`message_handler`) é o menos testado.
  Frontend: 42% de linhas — `ConversationDetailPage.tsx` 0%, `App.tsx` 0%, `lib/api.ts` 22%.
- **Ferramentas de dev na imagem de produção**: `pytest`, `ruff`, `bandit`, `pip-audit` e `aiosqlite`
  estão em `backend/requirements.txt`, que o `Dockerfile` instala. Mover para
  `requirements-dev.txt` (o arquivo já existe; falta remover de `requirements.txt`) reduz a imagem
  e a superfície de ataque. Exige ajustar o `deploy.yml` se ele usar `pytest` no build.

## Média prioridade

- **mypy strict (16)**: `dict` sem parâmetros de tipo em `api/*.py`, `main.py`, `db/session.py`,
  `models/tour.py`, `services/tour_matcher.py` (`dict[str, Any]`/`TypedDict`); `whatsapp_client.py:28`
  retorna `Any`; `transcription.py` sem retorno tipado e sem stubs do `faster_whisper`;
  `tests/test_webhook.py` (reexport de `whatsapp_client`). Nos testes o mypy tolera funções e
  chamadas de helpers sem tipos (override `tests.*` no `pyproject.toml`).
- **Docstrings** (`D1xx`): quase todos os módulos, classes e funções públicas de `app/` e `tests/`
  (tests já ignoram `D`). Escrever em pt-BR, estilo Google.
- **S105**: `app/core/config.py:38` (`whatsapp_verify_token` com valor literal por padrão — confirmar
  que o padrão não é um segredo utilizável em produção) e 3 tokens de teste em `tests/conftest.py`
  e `tests/test_security.py` (fixtures; marcar como constantes de teste).

## Baixa prioridade

- `ANN202`/`ANN204` (1 cada), `PLR0913` (1 função com > 5 parâmetros).
- Duplicação: as três entradas de `seed.py` e os setups repetidos de `test_webhook.py` e
  `ConversationsPage.test.tsx` viram helper/fixture ao serem tocados.
- Funções acima de 40 linhas: `services/message_handler.py:process_incoming_message` (50),
  `alembic/versions/0001_initial_schema.py:upgrade` (44, gerada), `tests/conftest.py:sample_tours` (45).
- `pytest-randomly` está ativo: se algum teste novo depender de ordem, ele aparece como flaky.

## Pontos de atenção do setup (não são dívida do código)

- Lockfile do backend: `requirements.txt` fixa versões diretas, mas não há lock com hashes.
- `.nvmrc` fixa Node 22; a máquina de desenvolvimento local está em Node 26 (gate e E2E passaram).
- `ruff==0.8.4` está antigo; subir a versão pode adicionar regras (rodar o gate ao atualizar).
- Frontend sem ESLint: a cobertura de regras vem de `tsc --strict`, Prettier e do verificador de
  tokens. Avaliar ESLint (`eslint-plugin-jsx-a11y`) para reforçar acessibilidade.
