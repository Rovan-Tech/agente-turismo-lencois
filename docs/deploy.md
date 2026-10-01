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
  bater entre backend e frontend).

Depois do primeiro deploy: configurar o webhook no painel da Meta
(`https://<url-do-cloud-run>/webhook/whatsapp`, com o mesmo `WHATSAPP_VERIFY_TOKEN`), proteger
`agente-turismo-lencois.pages.dev` com **Cloudflare Access** (barreira real de acesso ao
painel — ver Segurança acima), e checar branch protection da `main` exigindo o check `ci-ok`
(detalhes em `docs/ci-cd.md`).

O deploy confere a revisão nova com um teste de fumaça e **volta sozinho para a anterior** se ela
não responder saudável (`scripts/ci/verify_deploy.sh`); ver `docs/ci-cd.md`.
