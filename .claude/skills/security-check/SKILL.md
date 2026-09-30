---
name: security-check
description: Verificação de segurança completa do projeto - análise estática (bandit), auditoria de dependências (pip-audit, npm audit), revisão OWASP Top 10 do código alterado e pentest da API rodando localmente (assinatura forjada no webhook do WhatsApp, token do painel ausente/errado, injeção, payload malformado, upload/arquivo de áudio gigante, CORS, métodos inesperados). Corrige o que encontrar e cria teste de regressão para cada falha. Use antes de abrir PR que mexa em endpoint, webhook, banco ou autenticação, ou quando pedirem "pentest", "teste de segurança", "teste de invasão".
---

# security-check

**Escopo: só o próprio código e a aplicação rodando em `localhost`.** Nunca aponte ferramentas
ou payloads para hosts externos, produção ou serviços de terceiros (nem para `graph.facebook.com`
ou a API do Groq de verdade — mocke essas chamadas).

## 1. Mapear a superfície de ataque

Pontos de entrada deste projeto (`backend/app/api/`):

- `POST /webhook/whatsapp` — público, sem autenticação de usuário. Protegido só pela verificação
  HMAC (`X-Hub-Signature-256` contra `WHATSAPP_APP_SECRET`, `app/core/security.py`). Recebe
  payload da Meta, toca banco (cria `Conversation`/`Message`) e dispara chamadas externas (Groq,
  faster-whisper, WhatsApp Cloud API).
- `GET /webhook/whatsapp` — verificação do webhook (`hub.verify_token`), sem dado sensível.
- `GET /api/tours`, `GET /api/conversations`, `GET /api/conversations/{id}` — exigem
  `Authorization: Bearer <DASHBOARD_API_TOKEN>` (`app/api/deps.py`). Retornam dado pessoal do
  turista (telefone, conteúdo das mensagens) — superfície sensível pra LGPD.

Compare com `git diff origin/main...HEAD --stat` para focar no que mudou.

## 2. Análise estática e dependências

```bash
# backend
cd backend
bandit -r app -q
pip-audit -r requirements.txt

# frontend
cd frontend
npm audit --audit-level=high
```

Achado médio/alto no nosso código → corrigir. CVE em dependência → atualizar (sem versão
corrigida: registrar motivo e impacto no PR). Falso positivo → justificar, não silenciar.

## 3. Revisão manual (OWASP Top 10)

- **Injeção**: tudo que toca o banco passa pelo SQLAlchemy ORM (sem SQL cru montado com
  entrada do usuário); nada de `eval`/`exec`/`subprocess` com dado do webhook.
- **Autenticação/controle de acesso**: `/api/tours` e `/api/conversations` sem o header
  `Authorization` correto devem sempre retornar 401 (fail-closed — token vazio nunca libera
  acesso, ver `is_valid_dashboard_token`). O webhook sem assinatura válida (quando
  `WHATSAPP_APP_SECRET` está configurado) deve retornar 403.
- **XSS**: o painel (`frontend/src/pages/`) só renderiza texto via JSX (`{variavel}`), nunca
  `dangerouslySetInnerHTML` — conteúdo de mensagem do turista é dado externo não confiável.
- **Upload/entrada**: áudio do WhatsApp é baixado da Meta (não upload direto do usuário), mas o
  tamanho do arquivo baixado antes de passar pro faster-whisper deve ter um teto (DoS).
- **Exposição de dados**: erro do FastAPI não deve vazar stack trace (`debug=False` implícito,
  não usar `--reload`/debug em produção); segredos só em variáveis de ambiente
  (`backend/.env`, nunca commitado — ver `.env.example`).
- **CORS**: `CORSMiddleware` só libera `FRONTEND_ORIGIN`; confirmar que uma origem arbitrária
  não recebe `Access-Control-Allow-Origin`.
- **DoS**: payload do webhook e áudio transcrito não têm limite de tamanho hoje — ponto de
  atenção pra próximas mudanças que mexam em `resolve_incoming_text`/`transcribe_audio`.

## 4. Pentest local

Backend (rodar em background, mockando Groq/WhatsApp/faster-whisper — nunca chamar as APIs
reais):

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 &
```

Atacar **apenas `127.0.0.1:8000`**:

| Ataque | Exemplo | Esperado |
|---|---|---|
| Assinatura forjada no webhook | `curl -X POST /webhook/whatsapp -H "X-Hub-Signature-256: sha256=deadbeef" -d '{"entry":[]}'` (com `WHATSAPP_APP_SECRET` configurado) | 403 |
| Payload malformado no webhook | `curl -X POST /webhook/whatsapp -d 'isto nao e json {'` | 400, sem stack trace |
| Payload não-objeto no webhook | `curl -X POST /webhook/whatsapp -d '["array"]'` | 400 |
| Verificação do webhook com token errado | `GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=errado&hub.challenge=1` | 403 |
| Painel sem token | `curl /api/conversations` (sem header) | 401 |
| Painel com token errado | `curl /api/conversations -H "Authorization: Bearer errado"` | 401 |
| Método inesperado | `curl -X PUT /webhook/whatsapp` | 405 |
| CORS de origem não confiável | `curl /health -H "Origin: https://evil.example"` | sem `Access-Control-Allow-Origin` |
| Path traversal / rota inexistente | `curl /api/conversations/../../etc/passwd` | 404, sem vazar caminho interno |

A suíte automatizada (`backend/tests/test_security.py`) já cobre a maior parte disso via
`TestClient`/`AsyncClient` com dependências mockadas — rodar `pytest` cobre o que `curl` cobriria
manualmente. Use `curl` só pra confirmar comportamento end-to-end com o servidor de verdade de
pé, especialmente depois de mudar `app/main.py` ou `app/api/deps.py`.

Frontend: sem rotas de servidor próprias (SPA estática servida pelo Cloudflare Pages) — o
pentest relevante é conferir que nenhum dado sensível (token, telefone de turista) vaza no
bundle além do estritamente necessário (`VITE_API_TOKEN`, com a limitação já documentada no
CLAUDE.md) e que links externos usam `rel="noopener noreferrer"`.

Pare a aplicação ao fim (`kill %1` ou similar).

## 5. Corrigir e provar

Para cada falha: teste que reproduz o ataque (falhando) → correção mínima segura → suíte
completa passando. Se a correção mudar comportamento de negócio, pergunte antes.

## 6. Relatório

Para o usuário e na seção `## Security` do PR: ferramentas e resultado, vulnerabilidades →
correção → teste que cobre, riscos aceitos/pendentes com motivo (ex: limitação conhecida do
`VITE_API_TOKEN` embutido no bundle, mitigada pelo Cloudflare Access).

## 7. Manual V5: STRIDE, ASVS e LLM

- **STRIDE (`GOV-2`, `SEC-7`)**: para a superfície alterada, confira se existe modelo em
  `docs/threat-models/` (senão, `/threat-model`) e se cada mitigação tem teste em
  `backend/tests/test_security.py`.
- **Autenticação e taxa (`SEC-3`)**: endpoint novo protegido (fail-closed) ou público justificado,
  segredo comparado em tempo constante, teto de tamanho/volume (rate limit: TD-A3).
- **LLM (`AI-1`, `AI-2`)**: envie entrada adversária (mock do Groq, nunca a API real):
  "ignore as instruções anteriores…", mensagem gigante, HTML/SQL na mensagem e na resposta do
  modelo; confirme que o texto do turista fica delimitado como dado e que a saída é validada antes
  de ser enviada, gravada ou renderizada.
- **Privacidade (`SEC-6`)**: nenhum telefone, conversa, token ou áudio em log, URL ou console.
- **Segredos (`SEC-1`)**: varredura do diff por padrões de chave/token (gitleaks quando adotado).
- Registre o resultado por ID do checklist no relatório e na seção `## Security` do PR.
