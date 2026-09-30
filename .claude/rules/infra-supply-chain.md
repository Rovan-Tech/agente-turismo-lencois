---
paths:
  - "backend/Dockerfile"
  - ".github/**"
  - "docs/deploy.md"
  - "backend/requirements*.txt"
  - "frontend/package.json"
  - "frontend/public/**"
---

# Infraestrutura, cadeia de suprimentos e FinOps

Itens do checklist: `INF-1`..`INF-6`, `SEC-5`, `FE-5`. Deploy atual: Cloud Run + Cloudflare Pages +
Neon (`docs/deploy.md`). Serviço único, single-tenant: mTLS/service mesh (`INF-6`) e RLS são N/A por
ADR-0001 até existir um segundo serviço/cliente.

## Docker (`INF-1`)
- Multi-stage, base mínima, `USER` não-privilegiado (já é `app`, UID 10001), sem utilitários de shell
  desnecessários na imagem final, sem segredo em `ENV`/`ARG`. O `Dockerfile` atual ainda é
  single-stage (TD-I1): linhas novas seguem a regra, sem piorar.

## Imagem e proveniência (`INF-2`)
- Alvo: Trivy/Grype sem CVE crítica/alta, imagem assinada (Cosign) e SBOM CycloneDX no deploy
  (TD-I2, TD-A4). Não há etapa ainda (TD-I2). Requisito provisório: o `Dockerfile` do diff fixa a base (tag ou
  digest), não adiciona pacote de SO sem necessidade e `pip-audit` está limpo.

## CI/CD e IaC (`INF-3`)
- Workflows com `permissions:` mínimas (nunca o padrão amplo), actions em versão fixada (tag
  imutável ou SHA), segredo só por `secrets.*` e nunca em log/`echo`; Checkov (TD-I3).

## FinOps (`INF-4`, `FE-5`)
- **Custo zero é requisito.** Nenhum serviço pago, nenhuma dependência paga. Declare limites de
  CPU/memória/concorrência/instâncias máximas do Cloud Run no deploy.
- Bundle do painel ≤ 200 KB gzip por chunk; code splitting de rotas pesadas.

## Deploy sem downtime (`INF-5`)
- Mudança de risco usa revisão nova do Cloud Run com divisão de tráfego (canary gradual) e flag de
  desligamento (variável de ambiente é o mínimo sem custo); rollback automático se 5xx > 0,1% nos
  primeiros 10 minutos (TD-I4). Descreva o plano de rollback no PR.
