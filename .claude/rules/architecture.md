---
paths:
  - "backend/app/**"
  - "frontend/src/**"
---

# Arquitetura

## Backend (`backend/app/`)
Direção das dependências: `api/` (rotas) → `services/` → `models/`/`db/`; `core/` (config, segurança)
é folha. O domínio não importa FastAPI.

| Pasta | Contém | Proibido |
|---|---|---|
| `api/` | rotas FastAPI, `deps.py` (auth do painel), validação de entrada | regra de negócio, SQL |
| `services/` | groq, tour_matcher, transcription, whatsapp, message_handler | importar `fastapi` |
| `models/` `db/` | SQLAlchemy 2.0 async, sessão | lógica de negócio |
| `core/` | `Settings`, verificação HMAC | acessar banco |

- Rota fina: valida, chama um serviço, devolve resposta. ✅ `await handle_message(session, msg)`
  · ❌ montar prompt do Groq dentro da rota.
- Integração externa (Groq, WhatsApp) só via `services/`, injetável para teste.
- Migrations só via Alembic; SQL só via ORM/queries parametrizadas.

## Frontend (`frontend/src/`)
`pages/` orquestra → `components/` apresenta → `lib/` (api.ts, regras) sem React. Chamada HTTP só em
`lib/api.ts`. Estilo só por tokens (`styles/tokens.css`).

## Decisões fixas (não reabrir sem o teste de qualidade documentado)
Ver `docs/decisoes-de-arquitetura.md`: Groq como único LLM, faster-whisper self-hosted, sem
LibreTranslate, WhatsApp Cloud API oficial, sem persistir áudio bruto, custo zero de infra.
