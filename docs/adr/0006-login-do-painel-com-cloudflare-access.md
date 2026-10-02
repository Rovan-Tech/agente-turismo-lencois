# ADR-0006: Proteger o painel com Cloudflare Access e identificar cada pessoa pelo JWT

- **Status:** Aprovado (Patrick, 2026-10-01)
- **Data:** 2026-10-01
- **Autores:** Patrick (pedido); redação por Claude Code
- **Checklist afetado:** GOV-1, GOV-2, SEC-1, SEC-3, SEC-5, SEC-6, FE-3, DATA-3, INF-4, OBS-1
- **Motivação:** pré-requisito de segurança do atendimento humano (o atendente responder pelo
  painel no lugar da IA), que terá ADR próprio depois deste, e base do painel real **privado**:
  a vitrine pública do portfólio é uma demonstração sem backend, no
  [ADR-0007](0007-demonstracao-publica-do-painel-sem-backend.md).

## Contexto

Fatos, em 2026-10-01 (verificados no site em produção):

- `https://agente-turismo-lencois.pages.dev/` **abre sem login**: o HTML e o JavaScript são
  servidos a qualquer pessoa. O token do painel (`DASHBOARD_API_TOKEN`) vai **em texto dentro do
  bundle** (`VITE_API_TOKEN`). Quem baixa o JavaScript lê o token e chama a API do Cloud Run
  direto, que devolve conversas com telefone de turista (LGPD). Isso é a dívida TD-A6, que o
  `deploy.md` e o `security.md` tratam como "o Cloudflare Access ainda precisa ser ligado".
- O painel só **lê** e faz duas escritas leves (marcar status da conversa, CRUD de passeios).
  O recurso seguinte permitirá **enviar WhatsApp como a agência**: com a autenticação de hoje,
  qualquer pessoa na Internet poderia fazer isso.
- O painel está no Cloudflare Pages (`*.pages.dev`) e a API no Cloud Run (`*.run.app`): são
  **sites diferentes**, então um cookie de sessão do navegador não vai da página para a API sem um
  domínio comum ou um proxy na mesma origem.
- A documentação do Cloudflare (consultada hoje) confirma que o Access protege o `*.pages.dev` de
  produção (não só os previews), que o origin valida o cabeçalho `Cf-Access-Jwt-Assertion` com as
  chaves públicas em `<equipe>.cloudflareaccess.com/cdn-cgi/access/certs`, conferindo emissor e
  audiência, e que o Pages Functions faz proxy para outra origem. O plano gratuito do Pages
  Functions dá 100 mil requisições por dia.
- O `INGEST_API_TOKEN` (ADR-0005) é outro canal, do n8n, e não muda.
- O padrão do projeto pede, para senha, Argon2id; para sessão, cookie HttpOnly/Secure e
  nenhuma credencial em `localStorage` (`CLAUDE.md`, `security.md`).
- Custo zero é requisito.

## Opções avaliadas

1. **Cloudflare Access na frente do painel + proxy `/api/*` no Pages Functions + o backend valida
   o JWT do Access.** O Access cuida do login (código por e-mail ou Google, lista de pessoas
   permitidas). O navegador chama `/api/...` na **mesma origem** do painel; o Pages Function
   repassa a requisição ao Cloud Run com o cabeçalho `Cf-Access-Jwt-Assertion`; o backend valida
   assinatura, emissor, audiência e validade, e sabe **quem** é (claim `sub`/`email`). O token
   fixo sai do bundle. Prós: sem senha para guardar, identidade por pessoa (serve para uma ou
   várias pessoas, só muda a lista), revogação imediata no Cloudflare, auditoria por pessoa,
   custo zero (Access gratuito até 50 pessoas; 100 mil requisições por dia no Functions). Contras:
   depende do Cloudflare Zero Trust estar ativo na conta, uma dependência nova no backend para
   validar JWT (`PyJWT` com `cryptography`) e um proxy novo para manter.
2. **Login próprio no backend** (tabela de usuários no Neon, hash Argon2id, sessão em cookie pelo
   mesmo proxy). Prós: não depende do Cloudflare Zero Trust. Contras: o projeto passa a guardar
   senhas, e precisa de recuperação de senha, bloqueio por tentativas (hoje não há limite de
   taxa, TD-A3), tela de usuários e uma dependência (`argon2-cffi`): muito mais código e
   superfície de ataque para o mesmo resultado.
3. **Cloudflare Access só como porta de entrada, mantendo o token fixo.** Zero código: o bundle
   deixa de ser público. Contras: o token continua único e compartilhado (quem tem acesso o
   copia), sem identidade por pessoa nem revogação individual, e a API do Cloud Run segue
   aceitando esse token de qualquer lugar. Serve como **medida imediata**, não como solução.
4. **Não fazer nada.** O painel continua aberto e o recurso de responder pelo painel não pode ser
   construído com segurança.

## Decisão

Adotar a **opção 1**, em duas fases, com a opção 3 como **fase 0 imediata**:

- **Fase 0 (hoje, sem código):** ligar o Cloudflare Access no `agente-turismo-lencois.pages.dev`
  (Pages → Settings → Enable access policy; remover o `*` do subdomínio para proteger a produção),
  com uma política que permite só os e-mails da equipe. Fecha o painel aberto agora.
- **Fase 1 (este ADR):**
  - `frontend/functions/api/[[path]].ts`: proxy para o Cloud Run, com origem fixa por variável de
    ambiente, só `/api/` (sem `..` nem URL absoluta), só os métodos usados e `Cache-Control:
    no-store` na resposta. Nunca expõe `/webhook` nem `/api/ingest` (o n8n chama o Cloud Run
    direto, com o token próprio).
  - Backend: dependência `require_dashboard_auth` passa a aceitar o **JWT do Access**
    (`Cf-Access-Jwt-Assertion`), validado com as chaves da equipe (cache de 5 minutos, falha
    fechada), emissor (`ACCESS_TEAM_DOMAIN`) e audiência (`ACCESS_AUD`) fixos, algoritmo RS256
    apenas. O cabeçalho `Cf-Access-Authenticated-User-Email` **nunca** é confiado; só as claims
    do JWT verificado. O identificador da pessoa (`sub`) entra no log estruturado das mutações
    (status da conversa, CRUD de passeios), sem e-mail nem JWT.
  - Transição em `PANEL_AUTH_MODE`: `token` (hoje) → `both` (aceita os dois, para testar) →
    `access` (só JWT; o token fixo passa a responder 401). Sem as variáveis do Access, os modos
    `both` e `access` recusam tudo (falha fechada).
  - O frontend deixa de enviar `VITE_API_TOKEN` e chama `/api/...` na própria origem; o
    `DASHBOARD_API_TOKEN` deixa de existir no deploy ao fim da transição.
  - CORS do backend passa a não liberar nenhuma origem de navegador (o painel não fala mais com o
    Cloud Run direto).
  - **CSRF:** como a sessão agora é cookie (`CF_Authorization`), toda requisição que muda dado
    exige um cabeçalho próprio (`X-Panel-Request`), no proxy e no backend; uma página de terceiro
    não consegue enviá-lo sem pré-verificação CORS, que o painel não libera.

Decisões que dependem do Patrick estão em
[`docs/threat-models/2026-10-01-login-do-painel-cloudflare-access.md`](../threat-models/2026-10-01-login-do-painel-cloudflare-access.md).

## Consequências positivas

- O painel deixa de ser público e o token fixo sai do JavaScript.
- Cada ação passa a ter uma pessoa associada (`sub`), base do atendimento humano ("quem
  respondeu") e da auditoria (TD-A5).
- Adicionar ou remover alguém é editar uma lista no Cloudflare, sem senha nem deploy.
- Custo zero adicional.

## Riscos e trade-offs

- **Depende do Cloudflare Zero Trust.** É preciso ativá-lo na conta (o plano gratuito atende até
  50 pessoas; **confirmar se a ativação pede forma de pagamento**, o que conflitaria com custo
  zero). Se o Access cair, o painel fica inacessível (o atendimento da IA no n8n não depende dele).
- **Dependência nova no backend** (`PyJWT` com `cryptography`): justificar licença (MIT/Apache-2.0
  e BSD), fixar versão, `pip-audit` limpo (`SEC-5`).
- **Proxy novo para manter** no Pages Functions, com limite de 100 mil requisições por dia: o
  painel gera poucas, mas esgotar a cota deixa o painel fora do ar.
- **Cloud Run continua público** para o painel e para o n8n: a API do painel só responde com JWT
  válido, mas quem tem um JWT válido (a própria pessoa autorizada) pode usá-lo fora do navegador
  até ele expirar; a sessão do Access tem prazo configurável.
- **Todas as pessoas autorizadas têm o mesmo poder** (sem papéis). Papéis (por exemplo, só ler)
  ficam para quando houver necessidade.
- **Durante `both`**, o token fixo ainda funciona: a transição precisa terminar em `access`.

## Plano de adoção e reversão

1. Aprovação deste ADR e do threat model pelo Patrick (feita em 2026-10-01).
2. **Fase 0:** feita pelo Patrick no Cloudflare em 2026-10-01 e conferida pela API: aplicativo
   "Agente Turismo - Painel" no `agente-turismo-lencois.pages.dev`, só One-time PIN, sessão de 24
   horas, política "Equipe Rovan Tech - Painel" (2 e-mails exatos). Pendente: o `*` dos previews.
3. Testes primeiro (TDD): JWT inválido (expirado, audiência e emissor errados, `alg: none`, HS256
   com a chave pública, assinatura adulterada, `kid` desconhecido, JWKS fora do ar), modos de
   transição, CSRF, proxy sem abertura de SSRF, cabeçalho de e-mail ignorado.
4. Implementar o proxy, a validação no backend, a mudança do frontend e `PANEL_AUTH_MODE=both`;
   publicar com `both`, conferir o painel logado e, só então, passar para `access`.
5. Atualizar `deploy.md`, `security.md`, `README.md` e `tech-debt.md` (fechar TD-A6).
6. **Reversão:** voltar `PANEL_AUTH_MODE` para `both` ou `token` (o token fixo continua válido
   nesses modos) e, se preciso, desligar a política do Access no Cloudflare. O frontend sem o
   token exige redeploy do anterior.
