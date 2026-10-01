# CLAUDE.md

Guia para quem (humano ou Claude Code) for trabalhar neste repositório. Idioma: **nomes no código e
commits em inglês; docstrings, comentários e documentação em pt-BR.**

## O que é

Assistente de IA no WhatsApp para uma agência de turismo fictícia em Lençóis Maranhenses
(portfólio Rovan). O bot responde dúvidas sobre passeios em pt/en/es, transcreve áudios e o painel
React mostra as conversas e sinaliza as que precisam de atendimento humano. Meta de **custo zero**
de infra (Cloud Run, Cloudflare Pages, Neon, Groq) — ver `docs/decisoes-de-arquitetura.md`.

> **Em revisão:** o `docs/adr/0004-n8n-orquestra-gemini-vertex-numero-de-producao.md` (**Proposto**)
> descreve o fluxo que já roda em teste no n8n com Gemini (Vertex AI) e um número +55, o que sai do
> custo zero. Enquanto o Patrick não o aprovar, as regras de custo zero abaixo continuam valendo
> para código novo; o fluxo está em `docs/n8n/` e a análise de ameaças em `docs/threat-models/`.

## Mapa

```
backend/   Python 3.11 · FastAPI · SQLAlchemy async · Alembic · faster-whisper
  app/api  rotas (webhook, tours, conversations)   app/services  lógica (groq, matcher, whatsapp…)
  app/core config + HMAC                            app/models    Tour, Conversation, Message
  tests/   pytest (unitário, webhook, segurança)
frontend/  React 18 · TypeScript strict · Vite · Tailwind · React Router
  src/styles/tokens.css  design tokens (fonte única)   tests/unit  Vitest   tests/e2e  Playwright
scripts/   quality_gate.py (gate único) · check_design_tokens.py · check_limits.py
docs/      checklist-engenharia.md (padrão) · adr/ · threat-models/ · design-system.md · tech-debt.md
           decisoes-de-arquitetura.md · deploy.md · n8n/ (fluxo do WhatsApp exportado)
.claude/   rules/ · agents/ · hooks/ · skills/ (comandos) · settings.json
```

## Comandos

```bash
# backend (venv em backend/.venv, Python 3.11; instalar: pip install -r requirements-dev.txt)
cd backend && uvicorn app.main:app --reload      # dev (porta 8000)
alembic upgrade head && python -m app.seed       # migrations e catálogo
# frontend (Node do .nvmrc)
cd frontend && npm ci && npm run dev             # dev (porta 5173)
npm run test:e2e                                 # Playwright (sobe o preview na 4173)
# qualidade — MESMA fonte para hooks, subagents, pre-commit e CI
python3 scripts/quality_gate.py --fast           # só arquivos alterados (segundos)
python3 scripts/quality_gate.py --full           # tudo: fmt, lint, tipos, testes+cobertura, diff,
                                                 # duplicação, código morto, auditoria, E2E
make gate-fast | make gate                       # atalhos
```

## Padrão de engenharia (Manual V5): vale para todo código, sem exceção

O padrão do projeto é o **Manual Corporativo de Engenharia V5** (ISO 9001/27001/27034, OWASP ASVS e
LLM, SLSA, WCAG 2.2, LGPD), adaptado ao custo zero em `docs/adr/0001-adocao-do-manual-v5.md`. A fonte
única dos controles é **`docs/checklist-engenharia.md`**: 52 itens com ID (`GOV`, `GIT`, `GATE`,
`PY`, `FE`, `SEC`, `AI`, `OBS`, `DATA`, `INF`, `TEST`, `DOC`), cada um com o requisito impeditivo, o
dono (`reviewer` ou `qa`) e a única condição em que `N/A` vale.

- **Toda** alteração de código é medida por ele, por você (`/checklist`, antes) e pelos dois agents
  (depois). Os agents preenchem o checklist **inteiro a cada rodada**: `ID: OK|N/A|FALHA — evidência`.
- **Qualquer `FALHA` = REPROVADO.** Sem "aprovado com ressalvas", sem exceção por ser pequeno ou
  urgente. "Não consegui verificar" é `FALHA`, nunca `OK`. `N/A` só na condição objetiva da tabela.
- O hook `record_verdict` **recusa** relatório sem algum item, sem evidência ou com `APROVADO`
  contraditório (item em `FALHA`, BLOQUEANTE/IMPORTANTE, ❌), e o portão do Stop não deixa terminar.
- A regra pede algo que a infraestrutura ainda não tem? Item ⏳: vale o requisito provisório descrito
  e a lacuna está em `docs/tech-debt.md` (`TD-*`). **Não** é licença para pular.
- Antes do código: mudança arquitetural → `/adr` (aprovação do Patrick); funcionalidade crítica
  (endpoint, webhook, auth, dado pessoal, LLM) → `/threat-model` (STRIDE, mitigação vira teste).
- Regra errada ou impossível de cumprir? Pare e pergunte ao Patrick. Nunca edite o checklist, um
  limite, uma config de qualidade ou um hook para passar (o `protect_files` pede confirmação).

## Fluxo obrigatório (toda alteração de código)

```
implementar → code-reviewer ─reprovou→ corrigir → code-reviewer
                  │ aprovou
                  ▼
              qa-tester ─reprovou→ corrigir → volta ao code-reviewer
                  │ aprovou
                  ▼
               entregar
```

1. **Entender**: critérios de aceite; plano antes se a tarefa for grande ou ambígua. Ler o checklist e
   listar os itens acionados (e os `N/A` prováveis). ADR/threat model antes do código, se aplicável.
2. **Pesquisar**: context7 para as bibliotecas envolvidas.
3. **Implementar com testes** (TDD quando viável), seguindo `.claude/rules/`.
4. **Gate rápido** verde e **`/checklist`** sem `FALHA` antes de pedir revisão.
5. **Revisão**: subagent `code-reviewer` (checklist dos itens `reviewer`). REPROVADO → corrigir todo
   `FALHA`, BLOQUEANTE e IMPORTANTE e repetir.
6. **QA**: com a revisão aprovada, subagent `qa-tester` (checklist dos itens `qa`). REPROVADO → cada
   bug e cada `FALHA` vira teste ou correção verificável e **volta ao passo 5** (qualquer mudança de
   código invalida as aprovações, e o checklist é refeito por inteiro).
7. **Limite**: no máximo 3 rodadas por etapa; se não convergir, parar e explicar o impasse.
8. **Entrega**: relatório com o que mudou e por quê, vereditos com a contagem do checklist (OK · N/A ·
   FALHA) e os `N/A` justificados, evidências, sugestões e pendências.

**Briefing dos subagents** (eles não veem a conversa): objetivo, critérios de aceite, arquivos
alterados (o escopo: o resto da branch é de outra entrega) e branch base, caminhos do ADR/threat
model, itens que você considera `N/A` (com o motivo, para eles contestarem), como subir o app e rodar
testes e, da 2ª rodada em diante, o que mudou.
Subagents são somente leitura e terminam com `VEREDITO: APROVADO|REPROVADO` (um hook registra).

**Definição de pronto**: gate completo verde + code-reviewer e qa-tester APROVADOS para o código
atual **com checklist 100% `OK` ou `N/A` justificado (zero `FALHA`)** + ADR aprovado e threat model
quando exigidos + documentação afetada atualizada. Mudança só em `.md` dispensa o fluxo (mas
`docs/checklist-engenharia.md`, agents, rules, hooks e skills de fluxo contam como código).

Comandos: `/feature <descrição>` · `/bugfix <descrição>` · `/revisar` · `/qa` · `/gate` ·
`/checklist` (autoverificação) · `/adr <título>` · `/threat-model <funcionalidade>`.
Para abrir PR: `/prepare-pr` (só quando o Patrick pedir).

## Qual ferramenta usar

| Necessidade | Ferramenta |
|---|---|
| Documentação de biblioteca/framework/CLI | **context7** (`resolve-library-id` → `query-docs`) |
| Teste exploratório e evidências (screenshots, console, rede) | **Playwright MCP** |
| Teste E2E versionado | **Playwright** em `frontend/tests/e2e/` (TypeScript) |
| Validar no navegador real / fluxos com login | **Claude in Chrome**: iniciar com `claude --chrome` ou `/chrome` |

O Claude in Chrome é opcional e não fica no `.mcp.json`; o `qa-tester` funciona sem ele.

## Inegociáveis

- Nunca silenciar erro de lint, tipo ou teste para passar no gate (`# noqa`, `# type: ignore`,
  `skip`, `xfail`, limites rebaixados, asserts triviais). O `code-reviewer` reprova.
- Nunca afrouxar o padrão: nada de editar `docs/checklist-engenharia.md`, agents, hooks ou configs de
  qualidade para aprovar código; nada de `N/A` sem a condição da tabela; nada de aprovar com `FALHA`.
- Zero `any`, `Any` sem justificativa, `print`/`console.log`, `dangerouslySetInnerHTML`, credencial em
  `localStorage`, `extra="allow"`, CORS `*`, segredo, PII em log ou em prompt de LLM.
- Saída de LLM e entrada do usuário são dados não confiáveis (injeção de prompt, OWASP LLM).
- Nunca commit/push sem autorização do Patrick; nunca direto na `main` (protegida, só PR com CI verde).
- Nunca segredo em código, log ou commit. Nunca persistir áudio bruto — só a transcrição (LGPD).
- Cores/fontes só por tokens do design system. Toda mudança tem teste; bug = teste de regressão.
- Não adicionar LibreTranslate, Gemini ou outro LLM/tradução sem rodar o teste de qualidade de
  `docs/decisoes-de-arquitetura.md` — custo zero é requisito.
- Código legado: as regras valem para o que for novo/alterado; a dívida está em `docs/tech-debt.md`.
  Não refatore o que não foi pedido.

## Regras detalhadas (carregadas por caminho)

`.claude/rules/`: `python.md` · `typescript-react.md` · `architecture.md` · `testing.md` ·
`design-system.md` · `security.md` · `git.md` · `ai-governance.md` · `reliability-data.md` ·
`infra-supply-chain.md`. Deploy e secrets: `docs/deploy.md`.
Segurança do webhook/painel (HMAC, token, LGPD, Cloudflare Access): `.claude/rules/security.md`.

## Hooks (`.claude/hooks/`, config em `.claude/settings.json`)

Guarda de comandos perigosos · proteção de `.env`/segredos/lockfiles/configs de qualidade · qualidade
na hora após editar (ruff, tipos, tokens, padrões proibidos: `any`, `Any` sem justificativa,
`dangerouslySetInnerHTML`, credencial em storage, `extra="allow"`, CORS `*`, `print`/`console.*`…) ·
registro do veredito dos subagents, que **valida o checklist** (itens completos, evidência,
`APROVADO` sem `FALHA`) · **portão no Stop**
(código mudou sem APROVADO do reviewer e do QA → não termina) · contexto no início da sessão.
Após 3 bloqueios seguidos sem progresso o Stop libera com aviso.
Limites assumidos: o guarda de comandos é rede de segurança contra acidente (um script arbitrário
pode contorná-lo); subagents novos só existem depois de reiniciar o Claude Code; o gate mede
violações nas **linhas alteradas** e o legado fica em `docs/tech-debt.md` e `.mypy-baseline.json`. `.claude/state/` e
`.claude/reports/` só os hooks gravam.

## MCP

`.mcp.json`: `playwright` (`npx @playwright/mcp@latest`) e `context7` (HTTP; chave em
`CONTEXT7_API_KEY`, nunca no arquivo). Aprove os servidores ao abrir o projeto.
