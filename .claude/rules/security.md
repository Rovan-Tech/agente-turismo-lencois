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
- **Painel**: `/api/tours` e `/api/conversations` expõem telefone e conversas (LGPD) e exigem
  `Authorization: Bearer <DASHBOARD_API_TOKEN>` (`app/api/deps.py`, fail-closed). O token vai no
  bundle (`VITE_API_TOKEN`): a barreira real é o Cloudflare Access.
- **Segredos** só em `.env`/secrets do GitHub; nunca em código, log ou commit. Erros sem stack trace.
  CORS restrito ao domínio do painel. Menor privilégio (usuário não-root no Docker).
- **Áudio bruto nunca é persistido** (banco, disco, logs) — só a transcrição.
- **Dependências** auditadas: `pip-audit`, `npm audit --audit-level=high`; estática: `bandit`.
- Cada vulnerabilidade achada vira teste em `backend/tests/test_security.py` que envia o payload
  malicioso e confirma o bloqueio. Mudou superfície de ataque? Rode `/security-check` antes do PR.
- CSRF: não há formulários com sessão/cookie hoje; se surgirem, exigir proteção.
