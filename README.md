# agente-turismo-lencois

Assistente de IA no WhatsApp para uma agência de turismo **fictícia** em Lençóis Maranhenses
(Barreirinhas/MA), feito como projeto de portfólio da [Rovan Tech](https://rovantech.com.br).
Responde dúvidas sobre passeios em **português, inglês e espanhol**, recomenda o passeio certo para
o perfil do turista (idade, mobilidade, duração, preço) e sinaliza as conversas que precisam de
uma pessoa. Um painel web mostra as conversas, o catálogo, a agenda e as reservas.

## Como funciona

```
Turista ──WhatsApp──▶ Meta (Cloud API) ──webhook──▶ n8n ──▶ Gemini 2.5 Flash (Vertex AI)
                                                      │
                                    catálogo ◀── Backend (FastAPI + Postgres/Neon) ◀── Painel (React)
```

| Peça | Tecnologia | Onde roda |
|---|---|---|
| Orquestração do atendimento | n8n | n8n Cloud |
| IA | Gemini 2.5 Flash via Vertex AI | Google Cloud |
| Backend e API | Python 3.11, FastAPI, SQLAlchemy async, Alembic | Cloud Run |
| Banco | PostgreSQL | Neon |
| Painel | React 18, TypeScript, Vite, Tailwind | Cloudflare Pages |
| Mensagens | WhatsApp Business Cloud API (número +55) | Meta |

> **Estado da arquitetura.** O fluxo com n8n e Gemini está em operação de teste e descrito no
> [ADR-0004](docs/adr/0004-n8n-orquestra-gemini-vertex-numero-de-producao.md), ainda **Proposto**
> (aguarda aprovação). Enquanto isso, o backend mantém o fluxo original (webhook com HMAC,
> Groq, faster-whisper e gravação das conversas), que é a alternativa de reversão. As conversas
> de **texto** atendidas pelo n8n chegam ao painel por `POST /api/ingest/atendimentos`
> ([ADR-0005](docs/adr/0005-endpoint-de-entrada-para-o-n8n-registrar-atendimentos.md)); o áudio
> segue ignorado pelo n8n (TD-N4). Conversas sem atividade há 90 dias são apagadas (LGPD).
> **Em andamento:** uma pessoa da equipe poderá **assumir a conversa** e responder no lugar da IA
> ([ADR-0008](docs/adr/0008-atendimento-humano-pelo-painel.md)). O backend já tem as rotas; o painel
> e o fluxo do n8n ainda não, então por enquanto a IA continua respondendo.

## Pastas

```
backend/    API FastAPI, modelos, migrações Alembic e testes (pytest)
frontend/   Painel React com testes unitários (Vitest) e E2E (Playwright)
scripts/    Gate de qualidade e verificações do projeto
docs/       Decisões, checklist de engenharia, threat models, CI/CD, deploy e fluxo do n8n
.claude/    Regras, agentes e hooks usados com o Claude Code
```

## Rodando localmente

Pré-requisitos: Python 3.11, Node (versão do `.nvmrc`) e um Postgres **com SSL** (o backend sempre
conecta com `ssl=True`; use um banco de desenvolvimento no Neon).

```bash
make setup                                        # venv do backend, dependências e Playwright
cp backend/.env.example backend/.env             # preencha DATABASE_URL e DASHBOARD_API_TOKEN
cd backend && alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload                    # API em http://localhost:8000
cd ../frontend && npm ci && npm run dev          # painel em http://localhost:5173
```

Para receber mensagens reais do WhatsApp localmente é preciso expor a porta 8000 com um túnel
(cloudflared ou ngrok).

## Variáveis de ambiente do backend

Só os nomes; os valores nunca vão para o repositório (`backend/.env.example` tem os modelos).

`DATABASE_URL`, `DASHBOARD_API_TOKEN`, `INGEST_API_TOKEN`, `CONVERSATION_RETENTION_DAYS`, `HUMAN_HANDOFF_IDLE_HOURS`, `HUMAN_SEND_CAP_PER_HOUR`, `PANEL_AUTH_MODE`, `ACCESS_TEAM_DOMAIN`, `ACCESS_AUD`, `FRONTEND_ORIGIN`, `AGENCY_NAME`, `WHATSAPP_TOKEN`,
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `GROQ_API_KEY`,
`GROQ_MODEL`, `WHISPER_MODEL_SIZE`, `MAX_AUDIO_BYTES`.

O fluxo do n8n tem as próprias credenciais (WhatsApp, Google, o token do catálogo e o do registro de atendimentos); ver
[`docs/n8n/README.md`](docs/n8n/README.md).

## Qualidade

Uma única fonte de verdade para hooks, pre-commit e CI:

```bash
make gate-fast     # só os arquivos alterados (segundos)
make gate          # tudo: formatação, lint, tipos, testes e cobertura, duplicação, auditoria, E2E
cd backend && python -m pytest
```

Toda alteração de código passa pelo checklist de
[`docs/checklist-engenharia.md`](docs/checklist-engenharia.md) e por duas revisões (`code-reviewer`
e `qa-tester`) antes do merge. A `main` é protegida: só recebe mudanças por PR com o CI verde.
Convenções de commit e branch em [`.claude/rules/git.md`](.claude/rules/git.md).

## Segurança e privacidade

- Webhook da Meta com assinatura HMAC; painel e API protegidos por token.
- Texto do turista e saída da IA são tratados como dado não confiável (delimitação, limite de
  tamanho, validação de formato).
- Áudio bruto nunca é guardado, só a transcrição; telefone e conteúdo de conversa ficam fora dos
  logs (LGPD).
- Análise de ameaças: [`docs/threat-models/`](docs/threat-models/).

## Custos

O desenho original era de **custo zero** (faixas gratuitas de Cloud Run, Cloudflare Pages, Neon e
Groq). O ADR-0004 propõe sair disso: o Gemini no Vertex AI custa em torno de **US$ 0,00075 por
mensagem** e o n8n Cloud tem plano pago por execução (valores estimados; ver o ADR e
[`docs/tech-debt.md`](docs/tech-debt.md), item TD-N8). Responder a mensagens dentro de 24 horas do
contato do cliente não gera cobrança da Meta.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/adr/`](docs/adr/) | Decisões de arquitetura (ADR) e o fluxo de aprovação |
| [`docs/decisoes-de-arquitetura.md`](docs/decisoes-de-arquitetura.md) | Decisões anteriores ao processo de ADR |
| [`docs/threat-models/`](docs/threat-models/) | Modelos de ameaça (STRIDE) |
| [`docs/n8n/`](docs/n8n/) | Fluxo do WhatsApp no n8n, exportado e documentado |
| [`docs/deploy.md`](docs/deploy.md) e [`docs/ci-cd.md`](docs/ci-cd.md) | Deploy, rollback e pipeline |
| [`docs/tech-debt.md`](docs/tech-debt.md) | Dívida técnica e pendências |
| [`CLAUDE.md`](CLAUDE.md) | Guia para quem trabalha no repositório (pessoas e Claude Code) |
