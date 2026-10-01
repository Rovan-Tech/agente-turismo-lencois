---
paths:
  - "backend/app/**"
  - "backend/tests/test_security.py"
  - "frontend/src/**"
  - ".github/**"
---

# Segurança (OWASP Top 10 em toda mudança)

- **Entrada**: validar nas fronteiras (Pydantic; tipo e tamanho de áudio). **SQL**: só ORM/queries
  parametrizadas; nada de `eval`/`exec`/shell com entrada do usuário. **XSS**: nada de
  `dangerouslySetInnerHTML` com dado externo.
- **Webhook do WhatsApp** é o único endpoint público sem autenticação: a segurança depende da
  verificação HMAC (`X-Hub-Signature-256`) contra `WHATSAPP_APP_SECRET`, em tempo constante.
- **Painel**: `/api/tours` e `/api/conversations` expõem telefone e conversas (LGPD) e são
  protegidas por `require_dashboard_auth` (`app/api/deps.py`, fail-closed) conforme
  `PANEL_AUTH_MODE` (ADR-0006): `token` (Bearer `DASHBOARD_API_TOKEN`, que vai no bundle
  `VITE_API_TOKEN`), `both` ou `access` (só o JWT do Cloudflare Access, validado no backend, com
  o painel chamando `/api/*` pelo proxy do Pages). Os cabeçalhos de identidade do Access (e-mail)
  nunca são lidos; só as claims do JWT verificado.
- **Segredos** só em `.env`/secrets do GitHub; nunca em código, log ou commit. Erros sem stack trace.
  CORS restrito ao domínio do painel. Menor privilégio (usuário não-root no Docker).
- **Áudio bruto nunca é persistido** (banco, disco, logs) — só a transcrição.
- **Dependências** auditadas: `pip-audit`, `npm audit --audit-level=high`; estática: `bandit`.
- Cada vulnerabilidade achada vira teste em `backend/tests/test_security.py` que envia o payload
  malicioso e confirma o bloqueio. Mudou superfície de ataque? Rode `/security-check` antes do PR.
- CSRF: no caminho do JWT a sessão é cookie (`CF_Authorization`), então toda mutação exige o
  cabeçalho `X-Panel-Request: 1` (backend e proxy) e o CORS do navegador fica fechado em `access`.
  O token fixo vai num cabeçalho explícito e não precisa disso.

## Manual V5 (ISO 27001 / OWASP ASVS / STRIDE)
- **Antes do código** (`GOV-2`): STRIDE da funcionalidade crítica; mitigações viram testes.
- **Segredos (`SEC-1`)**: varredura de padrões de segredo no diff (gitleaks entra no CI: TD-A1).
  Segredo vazado é rotacionado, não só apagado do histórico.
- **Autenticação (`SEC-3`)**: endpoint novo nasce protegido (fail-closed) ou público por decisão
  justificada, com HMAC/verificação de origem e teto de tamanho/volume. Comparação de segredo em
  tempo constante (`hmac.compare_digest`). Senha (se um dia existir): Argon2id, nunca SHA/MD5.
- **Cabeçalhos e CSP (`FE-4`)**: alvo (TD-M7, o arquivo ainda não existe): `frontend/public/_headers` com CSP sem `unsafe-inline`/
  `unsafe-eval`, `X-Content-Type-Options`, `Referrer-Policy` e `frame-ancestors`.
- **Cadeia de suprimentos (`SEC-5`)**: dependência nova justificada, licença compatível e versão
  fixada; `pip-audit` e `npm audit` limpos; SBOM CycloneDX no CI (TD-A4).
- **Privacidade (`SEC-6`)**: minimização, pseudonimização quando o uso permitir, PII fora de
  log/console/URL, expurgo definido para dado pessoal novo, criptografia em trânsito e em repouso
  (avalie cifrar a coluna de campo sensível novo), áudio bruto nunca persistido.
