# Deploy

Movido do `CLAUDE.md`. Ver também a skill `/deploy-status` e `/redeploy`.

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
  bater entre backend e frontend) e `INGEST_API_TOKEN` (aleatório e forte, **diferente** do
  `DASHBOARD_API_TOKEN`: vai só ao backend e à credencial do n8n, nunca ao frontend; o backend
  se recusa a subir se os dois forem iguais). Sem ele, a rota de entrada do n8n responde 401.

Depois do primeiro deploy: configurar o webhook no painel da Meta
(`https://<url-do-cloud-run>/webhook/whatsapp`, com o mesmo `WHATSAPP_VERIFY_TOKEN`), proteger
`agente-turismo-lencois.pages.dev` com **Cloudflare Access** (**feito em 2026-10-01**; barreira real de acesso ao
painel — ver Segurança acima), e checar branch protection da `main` exigindo o check `ci-ok`
(detalhes em `docs/ci-cd.md`).

O deploy confere a revisão nova com um teste de fumaça e **volta sozinho para a anterior** se ela
não responder saudável (`scripts/ci/verify_deploy.sh`); ver `docs/ci-cd.md`.

## Login do painel (Cloudflare Access, ADR-0006)

O painel fica atrás do **Cloudflare Access** (aplicativo "Agente Turismo - Painel", login só por
código de uso único, política com os e-mails da equipe). A migração do token fixo para o login do
Access é controlada por **variáveis do repositório** (Settings → Secrets and variables → Actions →
**Variables**, não Secrets), lidas pelo `deploy.yml`:

| Variável | Valor |
|---|---|
| `PANEL_AUTH_MODE` | `token` (padrão, como era), `both` (token fixo **ou** Access) ou `access` (só Access) |
| `ACCESS_TEAM_DOMAIN` | `https://<equipe>.cloudflareaccess.com` |
| `ACCESS_AUD` | AUD tag do aplicativo no Access (Zero Trust → Access controls → Applications → o aplicativo) |

- **`token`**: o painel fala direto com o Cloud Run, com o token fixo no bundle (hoje em produção).
- **`both`** e **`access`**: o bundle sai **sem token** e chama `/api/*` na própria origem; a
  Pages Function (`frontend/functions/api/[[path]].ts`) repassa ao Cloud Run com o JWT do Access, que
  o backend valida (assinatura RS256, emissor, audiência, validade). `access` deixa o token fixo
  responder 401 e fecha o CORS do navegador.
- **Ordem da migração:** defina `ACCESS_TEAM_DOMAIN` e `ACCESS_AUD`, depois `PANEL_AUTH_MODE=both`
  e faça o deploy (`/redeploy`). Entre no painel (janela anônima, código por e-mail) e confira as
  telas e uma mudança (marcar uma conversa). Só então `PANEL_AUTH_MODE=access` e outro deploy.
- **Reversão:** volte `PANEL_AUTH_MODE` para `token` e faça o deploy; o token fixo e o bundle antigo
  voltam a valer. O Access na frente do `pages.dev` continua fechado ao público em qualquer modo.
- **Quem entra:** a política do aplicativo no Cloudflare. Adicionar ou tirar alguém não exige deploy.
- A origem do Cloud Run usada pelo proxy está em `frontend/wrangler.toml` (`API_ORIGIN`); se o
  serviço mudar de endereço, atualize-a.

## Expurgo de conversas (LGPD, ADR-0005)

O workflow `.github/workflows/retention.yml` roda todo dia (04:43 UTC) e sob demanda: apaga as
conversas sem atividade há mais de 90 dias **com as mensagens**, usando o secret `DATABASE_URL`. O
prazo é o padrão da aplicação (`CONVERSATION_RETENTION_DAYS`, mínimo 1): para mudá-lo, defina a
variável no `env` do workflow. O log traz só a quantidade apagada. Pelo prazo, o histórico do
painel tem 90 dias. Para rodar à mão: `cd backend && python -m app.purge_conversations`.

## Fluxo do WhatsApp no n8n (ADR-0004 e ADR-0005)

O atendimento também pode rodar no n8n Cloud, fora do `deploy.yml`: o n8n recebe o webhook da
Meta, lê o catálogo do backend (`GET /api/tours`, com o `DASHBOARD_API_TOKEN`), chama o Gemini no
Vertex AI e responde pelo número +55. Depois de responder, registra o atendimento no backend
(`POST /api/ingest/atendimentos`, com o `INGEST_API_TOKEN`) para o painel mostrar a conversa. O
workflow está exportado em `docs/n8n/` e **não é publicado por CI**: importe o JSON, troque
`<BACKEND_URL>` e `<GCP_PROJECT_ID>`, crie as cinco credenciais descritas em `docs/n8n/README.md` e
ative o workflow. **Ordem:** primeiro o secret `INGEST_API_TOKEN` e o deploy do backend, depois a
credencial e o workflow novo no n8n.

- **Na Meta:** número +55 registrado (*Inscrito*), **Assinar webhooks** ligado na conta e o
  callback do app apontando para a URL do gatilho do n8n (o n8n registra ao ativar).
- **Efeito no backend:** com o callback no n8n, `/webhook/whatsapp` deixa de receber mensagens; as
  conversas chegam ao painel pelo `POST /api/ingest/atendimentos`, só as de **texto** (o áudio
  segue ignorado pelo n8n, TD-N4).
- **Segredos:** token do usuário do sistema da Meta, chave da service account do Vertex e o
  `DASHBOARD_API_TOKEN` e `INGEST_API_TOKEN` ficam **só nas credenciais do n8n**, nunca no repositório. Os valores
  atuais de `WHATSAPP_*` no Cloud Run pertencem à conta de teste antiga.
- **Reversão:** desative o workflow, aponte o callback do app para
  `https://<backend>/webhook/whatsapp` com o `WHATSAPP_VERIFY_TOKEN` e atualize `WHATSAPP_TOKEN` e
  `WHATSAPP_PHONE_NUMBER_ID` no Cloud Run para os da conta de produção. Para só parar de gravar no
  painel, remova o nó HTTP do fluxo ou apague o `INGEST_API_TOKEN` (a rota passa a responder 401).
