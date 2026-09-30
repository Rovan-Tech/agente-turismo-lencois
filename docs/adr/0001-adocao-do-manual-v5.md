# ADR-0001: Adoção do Manual Corporativo V5 e adaptações ao projeto

- **Status:** Proposto (aguarda aprovação do Patrick)
- **Data:** 2026-09-30
- **Autores:** Patrick / Claude Code
- **Checklist afetado:** todos (`docs/checklist-engenharia.md`)

## Contexto

O _Manual Corporativo Global de Engenharia de Software, DevSecOps, SGI & Enterprise Standards
(Python & React) — V5_ define os controles que todo projeto Rovan deve seguir, sem exceção, e uma
matriz de code review (§11) com status `OK` ou `N/A`. Este projeto é um portfólio com **custo zero
de infraestrutura** (Cloud Run, Cloudflare Pages, Neon, Groq), serviço único, single-tenant, sem
fila, sem staging e sem Kubernetes. Parte dos controles do manual pressupõe infraestrutura que não
existe aqui (service mesh, SonarQube, Chaos Mesh, Unleash) e parte já é código (mypy strict, tokens
de design, HMAC).

## Opções avaliadas

1. **Aplicar o manual ao pé da letra, já.** Bloquearia todo PR até existirem OpenTelemetry, Cosign,
   Trivy, ZAP e outros; custo e prazo incompatíveis; o gate nunca ficaria verde.
2. **Adotar só o que já é cumprido.** Rápido, mas ignora o pedido de padronização sem exceção.
3. **Adotar tudo como checklist obrigatório, com adaptação rastreável (escolhida).** Cada controle
   do manual vira item do checklist; o que a infraestrutura ainda não suporta fica marcado ⏳ com
   requisito provisório verificável e dívida registrada; `N/A` só com condição objetiva.

## Decisão

Adotar o manual na opção 3. O checklist `docs/checklist-engenharia.md` é a fonte única; o
`code-reviewer` e o `qa-tester` o preenchem inteiro a cada rodada e o hook `record_verdict` recusa
relatórios incompletos ou com `APROVADO` contraditório. As regras valem para código novo ou
alterado; a conformidade do legado está em `docs/tech-debt.md` (_Conformidade com o Manual V5_).

### Tratamento de cada seção do manual

| Manual | Tratamento | Onde |
|---|---|---|
| §1 SGI (ISO 9001, 27001, 27034, SOC 2, OWASP ASVS, SLSA, 20000/22301, WCAG, LGPD) | Adotado; cada norma tem itens (SLO/DRP em `OBS-4`, pseudonimização e criptografia em repouso em `SEC-6`) | checklist |
| §2 ADR e STRIDE | Adotado (skills `/adr`, `/threat-model`) | `GOV-1`, `GOV-2` |
| §3 Clean/Hexagonal | **Adaptado**: a separação é por responsabilidade (`api/services/models`) e não pelos nomes `domain/application/...`; renomear é refatoração sem valor agora | `PY-1` |
| §3 Outbox, mypy strict, Pydantic strict, RFC 7807 | Adotado para código novo; não há mensageria (`PY-6` N/A até existir); handler RFC 7807 global é dívida. **Duas flexibilizações, ambas justificadas:** (1) o manual proíbe `Any` e `# type: ignore`; o projeto admite `Any` e `# type: ignore[codigo]` só com justificativa na mesma linha, por causa do payload JSON livre da Meta e de bibliotecas sem stubs (`faster-whisper`), e o hook acusa o que vier sem justificativa; (2) o manual exige `strict=True` sem exceção; o projeto abre uma só, `Field(strict=False)` com comentário, para tipos que o JSON não expressa (`datetime`, `UUID`, `Enum`, `Decimal`), pois o modo estrito os rejeitaria vindos como string | `PY-2..PY-6`, `GATE-4` |
| §4 Feature Slices, Zod, CSP, storage, CWV, lazy, Storybook | Adotado para código novo; nonce de CSP e Storybook ⏳ (Pages estático; Storybook pesado) | `FE-1..FE-8` |
| §5 DevSecOps (pre-commit, SAST, SCA/SBOM, IaC, mutação, DAST) | **Adaptado ao custo zero**: bandit + Semgrep + ruff `S` no lugar de SonarQube (substituição permanente); bloqueio de arquivo grande, SBOM, Checkov, mutação e ZAP ⏳ | `GIT-1`, `SEC-4/5`, `INF-3`, `TEST-2/3` |
| §6 Zero Trust/mTLS, Docker hardening, SLSA 3 | mTLS **N/A de arquitetura** (um serviço); Docker e Cosign ⏳ | `INF-1/2/6` |
| §7 MELT, resiliência, caos | Adotado para código novo; OpenTelemetry/Prometheus e caos em staging ⏳ | `OBS-1..3`, `PY-5` |
| §8 RLS, concorrência, auditoria | RLS **N/A de arquitetura** (single-tenant); concorrência adotada; auditoria com hash chain ⏳ (já no requisito de `DATA-3`) | `DATA-1..4` |
| §9 Governança de IA e OWASP LLM | Adotado (o projeto usa Groq); NeMo Guardrails/Llama Guard substituídos de forma permanente por delimitação + limite + filtro + teste adversário | `AI-1..3`, `GIT-3` |
| §10 FinOps e deploy | Custo zero mantido; bundle ≤ 200 KB gzip; canary via revisões do Cloud Run e flag por variável de ambiente ⏳ | `INF-4/5`, `FE-5` |
| §11 Matriz de code review | Adotado como o checklist; dois revisores = `code-reviewer` + `qa-tester`, mais aprovação humana do PR | checklist, `git.md` |

## Consequências positivas

- Um único padrão verificável por todos, com evidência registrada a cada rodada.
- `FALHA` em qualquer item reprova automaticamente; `N/A` exige justificativa objetiva.
- As lacunas de infraestrutura ficam visíveis e priorizadas em vez de escondidas.

## Riscos e trade-offs

- Relatórios dos agents ficam maiores (um item por linha) e cada rodada custa mais tokens.
- A coluna ⏳ pode virar desculpa permanente: por isso cada ⏳ tem um `TD-*` em `tech-debt.md` e um requisito provisório verificável; substituição permanente por custo não é ⏳, é decisão registrada aqui.
- `N/A` mal justificado: mitigado pela condição objetiva na tabela e pela revisão humana do PR.
- `DATA-4` e `INF-6` deixam de ser `N/A` no dia em que houver segundo cliente ou serviço; isso exige
  novo ADR antes do código.

## Plano de adoção e reversão

- Esta entrega: checklist, agents, hook de validação, rules, skills e `CLAUDE.md`.
- Próximos passos por prioridade: `tech-debt.md` → _Conformidade com o Manual V5_.
- Reversão: remover o hook de validação do `record_verdict`; o restante é documentação.
