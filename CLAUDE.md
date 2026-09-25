# CLAUDE.md

Guia para quem (humano ou Claude Code) for trabalhar neste repositório.

## O que é este projeto

Projeto de portfólio da Rovan: um assistente de IA no WhatsApp para uma agência de turismo
fictícia em Lençóis Maranhenses (Barreirinhas/MA). O bot responde dúvidas de turistas sobre
passeios (considerando dificuldade física, acessibilidade, duração, faixa etária e preço),
transcreve áudios recebidos e responde automaticamente em português, inglês ou espanhol
conforme o idioma do turista. O painel React mostra as conversas para a agência acompanhar e
sinaliza as que precisam de atendimento humano.

Decisão de arquitetura deliberada: **custo zero de infraestrutura**. Todo o stack roda nos
free tiers já usados em outros projetos Rovan (Cloud Run, Cloudflare Pages, Neon) mais o Groq
para o LLM. Por isso:

- **Groq** (`openai/gpt-oss-120b`) no lugar de hospedar um LLM local — evita cold start pesado
  no Cloud Run, que hiberna sem tráfego. Testado contra o Gemini API antes da decisão: o tier
  gratuito real do Gemini foi descontinuado (modelos atuais exigem crédito pré-pago), então
  Gemini não é usado neste projeto.
- **faster-whisper self-hosted** (modelo `base`, CPU) dentro do próprio backend — mensagens de
  voz do WhatsApp são curtas, então roda rápido mesmo sem GPU.
- **Sem LibreTranslate**: o teste de qualidade mostrou que o próprio Groq traduz bem sozinho
  (respostas nativas em pt/en/es), então uma camada extra de tradução seria redundante.
- **WhatsApp Business Cloud API oficial da Meta** (não Baileys/whatsapp-web.js): não arrisca
  banir o número real da agência e funciona via webhook, compatível com Cloud Run hibernando.
- **Não persistimos áudio bruto** — só a transcrição em texto. Minimiza dado sensível (LGPD) e
  evita precisar de storage de objeto (R2/S3), o que quebraria a meta de custo zero.

## Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async) + Neon Postgres, Alembic para
  migrations, faster-whisper para transcrição, httpx para Groq e WhatsApp Cloud API. Versão
  fixada em `backend/.python-version`.
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + React Router. Versão do Node
  fixada em `frontend/.nvmrc`.
- **Testes**: pytest (backend), Vitest + Testing Library (frontend, unitário), Playwright
  (frontend, e2e).
- **Deploy**: backend em Cloud Run (Docker), frontend em Cloudflare Pages, banco em Neon.

## Estrutura

```
backend/
  app/
    api/            # rotas FastAPI: webhook do WhatsApp, /api/tours, /api/conversations
    core/           # config (Settings) e segurança (verificação de assinatura do webhook)
    db/             # engine/sessão async e Base declarativa
    models/         # Tour, Conversation, Message (SQLAlchemy)
    services/       # groq_client, tour_matcher (RAG simples), transcription, whatsapp_client,
                     # message_handler (orquestra o fluxo ponta a ponta)
    seed.py         # popula o catálogo inicial de passeios
  alembic/          # migrations
  tests/            # pytest — unitário, integração do webhook e testes de segurança

frontend/
  src/
    components/     # StatusBadge, etc.
    pages/          # ConversationsPage (lista), ConversationDetailPage (thread de mensagens)
    lib/api.ts       # cliente HTTP pro backend
  tests/
    unit/           # Vitest + Testing Library
    e2e/            # Playwright
```

## Comandos

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # (ou source .venv/bin/activate no Linux/Mac)
pip install -r requirements.txt
uvicorn app.main:app --reload                     # dev
python -m app.seed                                # popula o catálogo de passeios
alembic upgrade head                              # aplica migrations
ruff check . && ruff format --check .             # lint/format
pytest                                            # testes unitários e de integração
bandit -r app -q && pip-audit -r requirements.txt # segurança estática e dependências

# frontend
cd frontend
npm install
npm run dev                                       # dev
npm run format:check                              # Prettier
npm run check                                     # tsc --noEmit
npm run test:unit                                 # Vitest
npx playwright install --with-deps chromium       # 1ª vez (sem --with-deps sem sudo)
npm run test:e2e                                  # Playwright
npm run build
npm audit --audit-level=high
```

## Testes são obrigatórios

Nenhuma funcionalidade é considerada pronta sem teste. Toda mudança nova ou alterada — por
menor que seja — vem acompanhada, **no mesmo PR**, de:

1. **Teste unitário** (pytest no backend, para lógica em `app/services/` e cada endpoint em
   `app/api/`, caminho feliz **e** de erro; Vitest no frontend, para lógica em `src/lib/` e
   componentes em `src/components/`/`src/pages/`).
2. **Teste end-to-end (Playwright)** para qualquer mudança visível ou interativa no painel —
   nova seção, novo fluxo, novo link, estado de erro/loading, comportamento mobile. Usar
   seletores semânticos (`getByRole`, `getByLabel`, `getByText`), nunca classes CSS. Specs em
   `frontend/tests/e2e/`.

Escrever o teste junto com o código (de preferência antes). Bug corrigido = teste de regressão
que falhava antes da correção. O CI roda tudo em todo push e PR; PR com teste quebrado ou
faltando não é mergeado.

## Segurança é obrigatória

Toda funcionalidade nova passa por:

1. **Revisão OWASP Top 10** do que foi alterado: injeção (SQLi — só SQLAlchemy ORM/queries
   parametrizadas; nada de `eval`/`exec`/shell com entrada do usuário), XSS (nada de
   `dangerouslySetInnerHTML` com dado externo no painel), validação de entrada e upload de
   áudio (tipo, tamanho), exposição de dados (erro sem stack trace, segredo só em `.env`), CORS
   restrito ao domínio do painel, controle de acesso, DoS. Ponto de atenção específico deste
   projeto: o webhook do WhatsApp é o único endpoint público sem autenticação — a segurança dele
   depende inteiramente da verificação de assinatura HMAC (`X-Hub-Signature-256`) contra o
   `WHATSAPP_APP_SECRET`. `/api/tours` e `/api/conversations` expõem telefone e conteúdo de
   conversas de turistas (dado pessoal, LGPD), então exigem `Authorization: Bearer
   <DASHBOARD_API_TOKEN>` (`app/api/deps.py`, fail-closed: sem token configurado, tudo é
   rejeitado). Limitação conhecida: o token é embutido no bundle do painel (`VITE_API_TOKEN`),
   então não é segredo pra quem inspecionar o JS — a barreira real de acesso ao painel é o
   Cloudflare Access na frente do domínio `*.pages.dev` (configuração manual, ver Deploy).
2. **Testes de segurança automatizados**: cada vulnerabilidade encontrada vira um teste que
   envia o payload malicioso e confirma o bloqueio, em `backend/tests/test_security.py`.
3. **Análise estática e de dependências**: `bandit -r app -q` e `pip-audit -r requirements.txt`
   no backend; `npm audit --audit-level=high` no frontend.
4. **Pentest local** antes de PR que mexa em superfície de ataque: skill `/security-check`, que
   roda as ferramentas, ataca a aplicação em `localhost` e **corrige** o que encontrar, sempre
   com teste de regressão.

## Estilo de código

Sem comentários explicando o óbvio — só quando uma decisão não for óbvia pelo código (ex: por
que não persistimos áudio bruto). Tipagem estrita em ambos os lados (type hints no Python,
`strict: true` no TypeScript). Lógica de negócio fica em `app/services/` (backend) e
`src/lib/`/hooks (frontend) — componentes e rotas só orquestram. Formatação automática via
`ruff format` (backend) e Prettier (frontend), sempre rodada antes de commitar.

## Deploy

Automático via `.github/workflows/deploy.yml`, disparado quando o job `CI` termina com sucesso
na `main` (mesmo padrão do `ocr-placas-previsao-filas`) — ou manualmente por
`workflow_dispatch` quando só um secret mudou e não há commit novo.

1. **Backend**: builda `backend/Dockerfile`, publica no Artifact Registry, roda
   `alembic upgrade head` e `python -m app.seed` (idempotente) contra o Neon **antes** de trocar
   o tráfego, depois publica no Cloud Run (`agente-turismo-lencois-backend`,
   `--allow-unauthenticated` — o webhook da Meta precisa alcançar o serviço sem autenticação de
   plataforma).
2. **Frontend**: builda `frontend/` com `VITE_API_BASE_URL` apontando pra URL do Cloud Run que
   acabou de subir e `VITE_API_TOKEN` = `DASHBOARD_API_TOKEN`, publica no Cloudflare Pages
   (projeto `agente-turismo-lencois`).

Secrets esperados no repositório GitHub (`Settings → Secrets and variables → Actions` —
segredos são por repositório, não herdam de outro, nem de org: confirmado que hoje este repo
não tem nenhum configurado):

- Reaproveitáveis do `ocr-placas-previsao-filas` (mesma infra Rovan): `GCP_WORKLOAD_IDENTITY_PROVIDER`,
  `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_ARTIFACT_REPO`,
  `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
- Novos deste projeto: `DATABASE_URL` (Neon — banco novo, não reaproveitar o do OCR),
  `GROQ_API_KEY`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`,
  `WHATSAPP_APP_SECRET`, `DASHBOARD_API_TOKEN` (qualquer string aleatória forte, só precisa
  bater entre backend e frontend).

Depois do primeiro deploy: configurar o webhook no painel da Meta
(`https://<url-do-cloud-run>/webhook/whatsapp`, com o mesmo `WHATSAPP_VERIFY_TOKEN`), proteger
`agente-turismo-lencois.pages.dev` com **Cloudflare Access** (barreira real de acesso ao
painel — ver Segurança acima), e checar branch protection da `main` exigindo os dois jobs do
`CI`.

## Antes de abrir PR

A `main` é protegida: só aceita mudanças via PR com o CI passando. Rode o skill `/prepare-pr`:
ele sincroniza a branch com a `main`, roda `/security-check` e os mesmos checks do CI
localmente, corrige o que falhar e abre o PR — ver `.claude/skills/prepare-pr/SKILL.md`.

## O que não fazer

- Não commitar credenciais, tokens ou IDs de serviços de terceiros (Groq, Meta, Neon,
  Cloudflare, Google Cloud).
- Não abrir PR sem os testes exigidos acima nem pular o `/security-check`.
- Não persistir áudio bruto do turista em nenhum lugar (banco, disco, logs) — só a transcrição.
- Não adicionar LibreTranslate, Gemini ou qualquer outro provedor de LLM/tradução sem antes
  rodar o mesmo teste de qualidade documentado na decisão de arquitetura acima — a meta de
  custo zero é um requisito do projeto, não um detalhe de implementação.
