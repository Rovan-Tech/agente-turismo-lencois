# CLAUDE.md

Guia para quem (humano ou Claude Code) trabalha neste repositório. Idioma: **nomes no código e
commits em inglês; docstrings, comentários e documentação em pt-BR.**

## O que é

Assistente de IA no WhatsApp para uma agência de turismo fictícia em Lençóis Maranhenses (portfólio
Rovan). O bot responde dúvidas sobre passeios em pt/en/es, transcreve áudios e o painel React mostra
as conversas e permite o atendimento humano. Decisões em `docs/adr/` e `docs/decisoes-de-arquitetura.md`;
o fluxo do WhatsApp (n8n + Gemini) está em `docs/n8n/`.

## Mapa

```
backend/   Python 3.11 · FastAPI · SQLAlchemy async · Alembic     (app/api, app/services, app/core, app/models, tests/)
frontend/  React 18 · TypeScript strict · Vite · Tailwind          (src/styles/tokens.css = tokens; tests/unit Vitest; tests/e2e Playwright)
scripts/   quality_gate.py (gate único) · check_design_tokens.py · check_limits.py
docs/      adr/ · threat-models/ · checklist-engenharia.md (referência) · tech-debt.md · deploy.md · n8n/
.claude/   rules/ (por caminho) · agents/ · hooks/ · skills/ (comandos do projeto)
```

## Comandos

```bash
cd backend && uvicorn app.main:app --reload       # dev (8000); alembic upgrade head && python -m app.seed
cd frontend && npm ci && npm run dev              # dev (5173); npm run test:e2e = Playwright
python3 scripts/quality_gate.py --fast            # só o que mudou (segundos)  = make gate-fast
python3 scripts/quality_gate.py --full            # tudo, igual ao CI           = make gate
```

## Como trabalhar (proporcional ao risco)

O **CI é a rede de segurança** (gate completo, CodeQL, Semgrep, SonarQube, gitleaks): não repita à mão
o que ele já faz. Faça o necessário para o tamanho da mudança:

1. **Entenda e implemente com teste** (bug = teste de regressão; TDD quando for natural). Siga
   `.claude/rules/`. Consulte o context7 só quando a API de uma biblioteca for incerta.
2. **Rode `make gate-fast`** e corrija o que falhar. Pronto para PR: `make gate`.
3. **Revisão independente só quando o risco pede**: autenticação, webhook, dado pessoal, LLM,
   migração de banco, infra ou mudança grande. Use `/revisar` (uma passada do `code-reviewer`, que
   olha só os itens do checklist que o diff aciona). `/qa` (E2E e exploratório) só se o Patrick pedir
   ou se a mudança é visual/de fluxo no painel. Mudança pequena, de docs ou de config: sem agents.
4. **Antes do código, só quando se aplica:** mudança arquitetural → `/adr` (o Patrick aprova);
   funcionalidade crítica nova (endpoint, webhook, auth, dado pessoal, LLM) → `/threat-model`
   curto, e cada mitigação vira teste.
5. **Entrega:** resumo do que mudou e por quê, o que foi verificado e o que ficou pendente. Sem
   relatório de checklist item a item.

`docs/checklist-engenharia.md` (Manual V5) é **referência**, não formulário: consulte os itens que a
mudança aciona (`/checklist` lista só esses). Quem ficou de fora vale como dívida em `docs/tech-debt.md`.
Se uma regra atrapalhar uma entrega razoável, diga qual e siga o caminho mais simples que o Patrick
aprovar. Não edite limites, configs de qualidade ou hooks só para fazer algo passar.

Comandos: `/feature` · `/bugfix` · `/revisar` · `/qa` · `/gate` · `/checklist` · `/adr` ·
`/threat-model` · `/clean-code` · `/security-check` · `/deploy-status` · `/redeploy` ·
`/prepare-pr` (só quando o Patrick pedir).

## Inegociáveis

- Nunca commit/push sem autorização do Patrick; nunca direto na `main` (protegida, só PR com CI verde).
- Nunca segredo em código, log ou commit; nunca PII em log ou prompt de LLM; nunca persistir áudio
  bruto (só a transcrição, LGPD).
- Entrada do usuário e saída de LLM são dados não confiáveis (injeção de prompt).
- Nada de `any`, `Any` sem justificativa, `print`/`console.log`, `dangerouslySetInnerHTML`,
  credencial em `localStorage`, `extra="allow"`, CORS `*`.
- Não silencie erro de lint, tipo ou teste (`# noqa`, `# type: ignore`, `skip`, `xfail`) nem rebaixe
  limites para passar no gate.
- Cores e fontes só por tokens do design system. Não refatore o que não foi pedido (legado em
  `docs/tech-debt.md`).

## Regras e hooks

`.claude/rules/` (carregadas por caminho): python · typescript-react · architecture · testing ·
design-system · security · git · ai-governance · reliability-data · infra-supply-chain. Deploy e
secrets: `docs/deploy.md`.

Hooks (`.claude/hooks/`, config em `.claude/settings.json`): guarda de comandos perigosos
(`guard_bash`), proteção de `.env`/chaves/lockfiles/configs de qualidade (`protect_files`),
qualidade após editar, registro de vereditos dos subagents e portão no Stop.
**Pendente (decisão do Patrick):** os três últimos ainda exigem o formato antigo de relatório
(checklist item a item) e bloqueiam o fim da resposta; ver o PR que enxugou esta configuração.

## MCP

`.mcp.json`: `playwright` e `context7` (chave em `CONTEXT7_API_KEY`, nunca no arquivo). Claude in
Chrome é opcional (`claude --chrome`).
