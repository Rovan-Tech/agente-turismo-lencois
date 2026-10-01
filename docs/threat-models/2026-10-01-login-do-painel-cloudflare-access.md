# Threat model: login do painel com Cloudflare Access (JWT validado no backend)

- **Data:** 2026-10-01
- **Escopo:** o caminho navegador → Cloudflare Access → Pages (`*.pages.dev`) → Pages Function
  (`/api/*`) → backend no Cloud Run, e a validação do JWT do Access no backend (ADR-0006). Fica de
  fora: o atendimento humano (ADR próprio), o `INGEST_API_TOKEN` do n8n (ADR-0005) e o webhook da
  Meta, que seguem como estão.
- **Dados sensíveis:** conversas e telefones de turistas (LGPD); o JWT do Access (cookie
  `CF_Authorization`); e-mail e identificador (`sub`) das pessoas da equipe; a configuração
  `ACCESS_TEAM_DOMAIN` e `ACCESS_AUD`.
- **Fronteiras de confiança:** Internet → Cloudflare Access (quem pode entrar); Pages Function →
  Cloud Run (origem fixa); navegador → painel (cookie de sessão); Cloud Run → JWKS do Cloudflare
  (chaves públicas). Tudo que chega ao backend é não confiável até o JWT ser verificado.

## Diagrama de fluxo (texto)

```
pessoa --login (e-mail/Google)--> Cloudflare Access --cookie CF_Authorization--> pages.dev (painel)
painel --fetch /api/... (mesma origem, X-Panel-Request em escrita)--> Access injeta Cf-Access-Jwt-Assertion
   --> Pages Function (só /api/*, origem fixa, no-store) --> Cloud Run
Cloud Run: JWT (RS256, chaves do JWKS em cache 5 min, emissor, audiência, validade) -> sub da pessoa
   --> rota do painel (CORS fechado; mutação exige X-Panel-Request; log com sub, sem JWT nem e-mail)
n8n --Bearer INGEST_API_TOKEN--> Cloud Run /api/ingest (inalterado; não passa pelo proxy)
```

## Ameaças (STRIDE)

Testes de backend em `backend/tests/test_panel_auth.py`; do proxy em
`frontend/tests/unit/apiProxy.test.ts`. Todos são escritos antes do código (TDD).

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | JWT forjado, adulterado, expirado ou emitido para outra aplicação ou equipe | Acesso às conversas e, no futuro, envio de WhatsApp como a agência | Validação de assinatura RS256 com as chaves do Cloudflare, `iss` e `aud` fixos, `exp` obrigatório | `test_panel_auth_rejects_invalid_claims[expired|wrong_audience|wrong_issuer|missing_exp|missing_sub|missing_iat]`, `test_panel_auth_clock_skew_tolerance_is_small`, `test_panel_auth_rejects_a_tampered_signature`, `test_panel_auth_rejects_a_token_signed_by_another_key` | Baixo |
| **S**poofing | Confusão de algoritmo: `alg: none` ou HS256 assinado com a chave pública | Contornar a verificação | Só RS256 aceito; o algoritmo não vem do token | `test_panel_auth_rejects_alg_none`, `test_panel_auth_rejects_hs256_signed_with_the_public_key` | Nenhum |
| **S**poofing | Cabeçalho `Cf-Access-Authenticated-User-Email` (ou qualquer outro) enviado por um atacante diretamente ao Cloud Run | Fingir ser outra pessoa | Só as claims do JWT verificado são usadas; os cabeçalhos de identidade são ignorados | `test_panel_auth_ignores_identity_headers_without_a_valid_jwt` | Nenhum |
| **S**poofing | Chamar o Cloud Run direto (sem passar pelo Access) com o token fixo antigo | Contornar o login | No modo `access` o token fixo responde 401; no `both`, é exceção temporária e visível | `test_panel_auth_mode_access_rejects_the_static_token`, `test_panel_auth_mode_both_accepts_the_static_token_or_the_jwt`, `test_panel_auth_mode_token_ignores_the_access_jwt` | Médio durante `both`; fecha ao passar para `access` |
| **S**poofing | Configuração incompleta (sem `ACCESS_AUD` ou `ACCESS_TEAM_DOMAIN`) aceita qualquer coisa | Painel aberto por engano | Nos modos `both` e `access`, variável ausente = 401 sempre (falha fechada) | `test_panel_auth_without_access_settings_rejects_every_jwt[access|both]`, `test_panel_auth_incomplete_access_settings_never_reach_the_validation` | Nenhum |
| **T**ampering | JWKS indisponível, lento ou devolvendo chave inesperada | Aceitar token sem verificar, ou travar | Falha fechada (401/503), timeout curto, cache de 5 min, `kid` desconhecido recusado | `test_panel_auth_jwks_failure_fails_closed`, `test_panel_auth_any_failure_fetching_the_jwks_is_a_503[connection_reset|invalid_json_body]`, `test_panel_auth_unknown_kid_is_rejected` | Baixo: painel fora do ar se o Cloudflare estiver fora |
| **T**ampering | O proxy vira um proxy aberto (SSRF): caminho com `..`, URL absoluta, esquema estranho, método inesperado | Usar o Pages para atacar outras origens ou chegar a `/webhook` e `/api/ingest` | Origem fixa por variável e **lista de permitidos**: só `/api/tours` e `/api/conversations` com segmentos de letras, números, `_` e `-` (sem `%`, `.` nem barra no fim, o que barra `%69ngest`, dot-segments e codificações por construção); métodos GET/PUT/PATCH/DELETE/POST; corpo declarado até 64 KiB; resposta sem `Location`, `Set-Cookie` nem cabeçalhos CORS do backend | `api proxy rejects <caminhos perigosos> without calling the origin` (absoluto, `..`, codificados, barra invertida, segmento vazio, `/api/ingest`), `api proxy rejects the OPTIONS|HEAD method`, `api proxy answers 500 when the origin is missing|not https|has a path` (Vitest) | Baixo |
| **T**ampering | CSRF: outra página faz o navegador da pessoa enviar uma mutação com o cookie do Access | Ação indevida (mudar status, e no futuro enviar mensagem) | Cookie com `SameSite` restrito (ajuste no Access) **e** cabeçalho `X-Panel-Request` obrigatório em toda mutação, no proxy e no backend; CORS fechado impede o envio cruzado com cabeçalho próprio | `test_panel_auth_mutation_without_the_exact_panel_header_is_rejected[PATCH conversa|POST/PUT/DELETE passeio x None|vazio|0|true|11]`, `test_panel_auth_mutation_with_panel_header_reaches_the_route`, `test_app_cors_follows_the_panel_auth_mode`, `api proxy rejects a POST|PUT|PATCH|DELETE without the panel header`, `lib/api sends the panel header on a change` | Baixo |
| **R**epudiation | Não saber quem mudou o quê | Disputa sem prova | O `sub` da pessoa entra no log estruturado de cada mutação (status da conversa, CRUD de passeios), sem e-mail nem JWT | `test_panel_auth_mutation_logs_the_actor_sub_without_email_or_jwt` | Médio: sem tabela de auditoria append-only (TD-A5) |
| **I**nformation disclosure | JWT ou e-mail nos logs, em erros ou na URL | Vazamento de credencial e de dado pessoal | O JWT só é lido do cabeçalho, nunca registrado; erro 401 sem detalhe do token; sem credencial em query | `test_panel_auth_never_logs_the_jwt_or_email`, `test_panel_auth_error_does_not_echo_the_token` | Baixo |
| **I**nformation disclosure | Resposta com conversas guardada em cache do Cloudflare ou do navegador e vista por outra pessoa | Vazamento de telefone e texto | O proxy responde `Cache-Control: no-store` em `/api/*` | `api proxy marks responses as no-store and drops set-cookie` | Baixo |
| **I**nformation disclosure | Painel de produção ou previews acessíveis sem login por esquecer um hostname | Painel aberto em um endereço | A política do Access cobre `*.pages.dev` de produção **e** previews; conferir por uma requisição sem cookie | Manual (checklist da Fase 0): requisição sem cookie recebe a página de login do Access | Médio até a Fase 0 ser feita e conferida |
| **D**enial of service | Cota gratuita do Pages Functions (100 mil por dia) esgotada, ou JWKS pedido a cada requisição | Painel fora do ar | Cache do JWKS por 5 min; painel de baixo tráfego; o atendimento da IA (n8n) não passa pelo proxy | `test_panel_auth_caches_the_jwks_between_requests`, `test_panel_auth_jwks_outage_is_remembered_instead_of_refetched_per_request` | Baixo |
| **D**enial of service | Cloudflare Access fora do ar | Ninguém abre o painel | Aceito: o atendimento do turista não depende dele | n/a | Baixo |
| **E**levation of privilege | Pessoa autorizada com acesso total (sem papéis) ou JWT roubado usado fora do navegador até expirar | Uso indevido por quem já está autorizado, ou por quem roubou o JWT | Lista de pessoas curta e revisável; expiração de sessão curta no Access; revogação no Cloudflare. Papéis ficam para depois | n/a | Médio: aceito (ver abaixo) |
| **E**levation of privilege | O JWT do painel serve nas rotas do n8n ou o token do n8n serve no painel | Atravessar fronteiras | O ingest continua só com `INGEST_API_TOKEN`; o painel só com JWT (ou token fixo durante `both`) | `test_ingest_rejects_the_panel_jwt`, `test_ingest_token_is_rejected_by_dashboard_routes` | Nenhum |

## Decisões

Tomadas pelo Patrick em 2026-10-01 (aprovação do ADR-0006):

1. **Zero Trust:** já estava ativo na conta, sem pedir forma de pagamento (há um Access de
   staging em uso). Fase 0 concluída.
2. **Quem entra e como:** política "Equipe Rovan Tech - Painel", 2 e-mails exatos, login só por
   One-time PIN.
3. **Sessão:** 24 horas.
4. **Transição:** `token` → `both` → `access`; o tempo em `both` é curto (conferir o painel logado).
5. **Dependência nova:** `PyJWT` com `cryptography` no backend, aprovada.

## Riscos aceitos

- Todas as pessoas autorizadas têm o mesmo poder; papéis ficam para quando houver necessidade.
  **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0006).**
- O backend no Cloud Run continua alcançável pela Internet; só responde ao painel com JWT válido.
  **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0006).**
- Dependência do Cloudflare: se o Access cair, o painel fica fora até ele voltar.
  **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0006).**
