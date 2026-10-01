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
2. **Frontend**: builda `frontend/` e publica no Cloudflare Pages (projeto
   `agente-turismo-lencois`). No modo `token` (padrão) usa `VITE_API_BASE_URL` apontando pra URL do
   Cloud Run que acabou de subir e `VITE_API_TOKEN` = `DASHBOARD_API_TOKEN`; nos outros modos o
   bundle sai sem token e com `VITE_API_BASE_URL` vazio (ver "Login do painel").

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
- **Antes de `access`, procure quem mais usa o token fixo.** O n8n lia o catálogo com ele; agora lê
  em `/api/ingest/catalogo` com o `INGEST_API_TOKEN`. Qualquer outro cliente do `DASHBOARD_API_TOKEN`
  (script, monitor) deixa de funcionar no modo `access`.
- **Ordem da migração:** defina `ACCESS_TEAM_DOMAIN` e `ACCESS_AUD`, depois `PANEL_AUTH_MODE=both`
  e faça o deploy (`/redeploy`). Entre no painel (janela anônima, código por e-mail) e confira as
  telas e uma mudança (marcar uma conversa). Só então `PANEL_AUTH_MODE=access` e outro deploy.
- **Reversão:** volte `PANEL_AUTH_MODE` para `token` e faça o deploy; o token fixo e o bundle antigo
  voltam a valer.
- **Previews ainda abertos:** o Access cobre hoje só `agente-turismo-lencois.pages.dev`. As URLs de
  preview e por hash (`*.agente-turismo-lencois.pages.dev`) **não** estão atrás do Access: em modo
  `token` o bundle delas traz o token fixo, e em `both`/`access` o proxy responde ali sem Access e só
  a validação do JWT no backend protege. **Antes de ligar `both`**, edite o aplicativo no Cloudflare
  e acrescente o hostname `*.agente-turismo-lencois.pages.dev` (Subdomain `*`) na mesma política.
- **Conferir na fase `both`, antes de passar para `access`:** (1) o painel abre logado e as telas
  carregam; (2) uma mudança funciona (marcar uma conversa), o que prova o JWT, o proxy e o cabeçalho
  anti-CSRF; (3) o log do Cloud Run não mostra "chaves do Cloudflare Access indisponíveis" (o backend
  alcança o JWKS da equipe com o `User-Agent` próprio); (4) o `API_ORIGIN` do `wrangler.toml` vale em
  produção: se faltar, o proxy responde 500 "proxy mal configurado".
- **Sessão expirada:** depois das 24 horas o Access redireciona a requisição para o login e o painel
  mostra um erro genérico; recarregar a página leva ao login.
- **Quem entra:** a política do aplicativo no Cloudflare. Adicionar ou tirar alguém não exige deploy.
- A origem do Cloud Run usada pelo proxy está em `frontend/wrangler.toml` (`API_ORIGIN`); se o
  serviço mudar de endereço, atualize-a.

## Expurgo de conversas (LGPD, ADR-0005)

O workflow `.github/workflows/retention.yml` roda todo dia (04:43 UTC) e sob demanda: apaga as
conversas sem atividade há mais de 90 dias **com as mensagens**, usando o secret `DATABASE_URL`. O
prazo é o padrão da aplicação (`CONVERSATION_RETENTION_DAYS`, mínimo 1): para mudá-lo, defina a
variável no `env` do workflow. O log traz só a quantidade apagada. Pelo prazo, o histórico do
painel tem 90 dias. Para rodar à mão: `cd backend && python -m app.purge_conversations`.

## Atendimento humano pelo painel (ADR-0008)

> **Ordem de entrada em produção:** (1) backend (já no ar); (2) painel (botões e campo de
> resposta); (3) **só então** importar o fluxo novo no n8n. O fluxo exportado em `docs/n8n/` já
> traz a consulta de atendimento, mas o n8n é publicado à mão: **até ele ser atualizado, assumir a
> conversa não silencia a IA**. Não oriente a equipe a usar antes de conferir os três passos.

A pessoa logada assume a conversa no painel e responde **pelo backend**, que envia pela Cloud API da
Meta. Para isso o backend precisa dos dados do número **de produção**:

- **Secrets do GitHub** (`WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID`): hoje guardam a conta de
  teste antiga. Troque-os pelos do número +55 (token do usuário do sistema, escopo só de
  mensagens) antes de testar de verdade, **sem colar o valor no chat nem no repositório**. Se o
  token vazar, rotacione-o na Meta e atualize o secret.
- **Janela de 24 h:** a Meta só aceita texto livre até 24 h depois da última mensagem do turista
  (erro `131047`); o painel desabilita o campo e o backend recusa com 409.
- **Ajustes** (opcionais, no `env` do deploy): `HUMAN_HANDOFF_IDLE_HOURS` (padrão 2: sem mensagem do
  atendente por esse tempo, a conversa volta para a IA) e `HUMAN_SEND_CAP_PER_HOUR` (padrão 60
  mensagens de atendente por conversa por hora).
- **Quem pode:** só quem entra pelo login do Access (o token fixo do painel recebe 403 em
  assumir, devolver e enviar). O nome que o turista vê é o primeiro nome do e-mail do login.
- **n8n:** antes de chamar o Gemini o fluxo pergunta `POST /api/ingest/conversas/atendimento` (telefone
  no corpo; com o `INGEST_API_TOKEN`); com `humano` ele só registra a mensagem em
  `POST /api/ingest/mensagens` e não responde. **Ordem:** deploy do backend, depois o fluxo.
- **Migração `0004`:** colunas novas em `conversations` e `messages`; `alembic downgrade 0003`
  desfaz (as mensagens de atendente continuam no histórico; só se perde a informação de quem escreveu). A migração do agendamento passa a `0005`.

## Fluxo do WhatsApp no n8n (ADR-0004 e ADR-0005)

O atendimento também pode rodar no n8n Cloud, fora do `deploy.yml`: o n8n recebe o webhook da
Meta, lê o catálogo do backend (`GET /api/ingest/catalogo`, com o `INGEST_API_TOKEN`), chama o Gemini no
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
  `INGEST_API_TOKEN` ficam **só nas credenciais do n8n**, nunca no repositório (o n8n não usa o
  `DASHBOARD_API_TOKEN`: ele lê o catálogo em `/api/ingest/catalogo`). Os valores
  atuais de `WHATSAPP_*` no Cloud Run pertencem à conta de teste antiga.
- **Reversão:** desative o workflow, aponte o callback do app para
  `https://<backend>/webhook/whatsapp` com o `WHATSAPP_VERIFY_TOKEN` e atualize `WHATSAPP_TOKEN` e
  `WHATSAPP_PHONE_NUMBER_ID` no Cloud Run para os da conta de produção. Para só parar de gravar no
  painel, remova o nó HTTP do fluxo ou apague o `INGEST_API_TOKEN` (a rota passa a responder 401).
