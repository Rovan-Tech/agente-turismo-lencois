# Checklist de engenharia (Manual Corporativo V5)

Fonte única dos controles que **todo** código alterado precisa cumprir. Derivado da matriz do §11 do
_Manual Corporativo Global de Engenharia de Software, DevSecOps, SGI & Enterprise Standards
(Python & React) — V5_ e adaptado ao que o projeto roda hoje (custo zero: Cloud Run, Cloudflare
Pages, Neon, Groq). A adaptação está justificada em `docs/adr/0001-adocao-do-manual-v5.md`.

O `code-reviewer` e o `qa-tester` **preenchem este checklist inteiro a cada rodada** (não só o que
mudou) e o hook `record_verdict` **recusa** o relatório se faltar item, se faltar evidência ou se
houver `FALHA` com veredito `APROVADO`. Itens novos entram aqui e passam a ser exigidos
automaticamente: o hook lê a tabela abaixo.

## Como preencher

Uma linha por item, na seção `Checklist:` do relatório do agente:

```
ID: OK — evidência concreta (arquivo:linha, comando, saída)
ID: N/A — por que a condição de N/A da tabela vale para este diff
ID: FALHA — arquivo:linha, o que está errado, como corrigir
```

- **OK** exige evidência verificável. "Parece bom" não é evidência.
- **N/A** só vale na condição da última coluna; fora dela, o item se aplica. A justificativa cita o
  fato (ex.: "diff só altera `frontend/src/components/Brand.tsx`, sem endpoint"), não a opinião.
- **FALHA** em qualquer item ⇒ veredito **REPROVADO**, sem exceção e sem "aprovado com ressalvas".
  Só sai de `FALHA` corrigindo o código (ou o ADR/teste que faltava), nunca editando este arquivo,
  baixando um limite ou silenciando a ferramenta.
- Coluna **Enquanto a base não existe** (⏳): o manual exige algo que a infraestrutura do projeto
  ainda não tem (ex.: OpenTelemetry). O requisito vale como descrito nessa coluna e a lacuna fica
  em `docs/tech-debt.md` (seção _Conformidade com o Manual V5_). O ⏳ **não** autoriza N/A.
- Regras de legado: valem para o que é novo ou alterado; não refatore o que não foi pedido.

**Dono**: `reviewer` (code-reviewer, leitura do código e do diff) ou `qa` (qa-tester, execução da
aplicação, do gate completo e da E2E).

## Matriz

| ID | Controle | Requisito impeditivo | Enquanto a base não existe (⏳) | Dono | N/A só se |
|---|---|---|---|---|---|
| GOV-1 | ADR | Mudança arquitetural (banco, nova biblioteca de infraestrutura, novo padrão de comunicação, novo provedor de LLM) tem ADR aprovado em `docs/adr/` com Contexto, Opções avaliadas, Decisão, Consequências positivas e Riscos/trade-offs | — | reviewer | o diff não altera arquitetura nem adiciona dependência de infraestrutura |
| GOV-2 | Threat model STRIDE | Funcionalidade crítica (endpoint, webhook, autenticação, dado pessoal, chamada a LLM) tem modelo STRIDE em `docs/threat-models/` (Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege) e cada mitigação virou teste automatizado | — | reviewer | o diff não cria nem altera fronteira de confiança nem trata dado sensível |
| GOV-3 | Rastreabilidade (ISO 9001) | Cada critério de aceite tem pelo menos um teste que o prova; nenhum critério ficou sem cobertura | — | reviewer | — (sempre se aplica) |
| GIT-1 | Higiene de repositório | Nenhum arquivo sensível, temporário ou gerado no diff (`.env`, chaves, dumps, `__pycache__`, `.qa-artifacts`, builds); `.gitignore` cobre o que foi criado; nenhum arquivo > 500 KB sem justificativa | ⏳ o pre-commit não bloqueia arquivo grande (`check-added-large-files`, TD-G1): o reviewer confere o tamanho dos arquivos novos | reviewer | — |
| GIT-2 | Branch e commits | Trabalho em `feat/`, `fix/` ou `chore/`; nada direto na `main`; commits existentes em inglês, Conventional Commits, atômicos | — | reviewer | — |
| GIT-3 | Anti-AI-slop | Sem `print`/`console.*`/`debugger`, sem código comentado, sem comentário redundante, sem TODO sem referência, sem função, import ou parâmetro fantasma; o revisor consegue explicar cada trecho novo | — | reviewer | — |
| GATE-1 | Gate rápido | `python3 scripts/quality_gate.py --fast` verde, rodado pelo próprio agente | — | reviewer | — |
| GATE-2 | Gate completo | `python3 scripts/quality_gate.py --full` verde (formatação, lint, tipos, testes, duplicação, código morto, auditorias, build, E2E inteira) | — | qa | — |
| GATE-3 | Cobertura | Cobertura das linhas alteradas ≥ 90% e cobertura global não cai abaixo da linha de base | — | qa | — |
| GATE-4 | Anti-gambiarra | Nenhum `# noqa`/`# type: ignore` sem código e porquê, `@ts-ignore`, `skip`/`xfail`/`.only`, limite rebaixado, config de qualidade afrouxada, assert trivial ou exceção engolida | — | reviewer | — |
| PY-1 | Arquitetura em camadas | `api/` → `services/` → `models/db/`; `core/` é folha; regra de negócio sem importar FastAPI nem ORM; rota fina; integração externa só em `services/` e injetável | — | reviewer | o diff não toca `backend/app/` |
| PY-2 | Tipagem estática total | `mypy --strict` sem erro novo; sem `Any` injustificado; sem `# type: ignore` sem código; tipos completos em funções e atributos públicos | — | reviewer | o diff não toca Python |
| PY-3 | Contratos Pydantic v2 | Schema de entrada novo ou alterado usa `ConfigDict(strict=True, extra="forbid")`, com limites de tamanho e intervalo (evita Parameter Pollution). Única exceção: campo cujo tipo o JSON não expressa (`datetime`, `UUID`, `Enum`, `Decimal`) usa `Field(strict=False)` com comentário do porquê | ⏳ schemas legados sem `strict`/`extra="forbid"` (TD-M8): ao alterar um, corrija |  reviewer | o diff não cria nem altera schema de entrada |
| PY-4 | Erros (RFC 7807) | Resposta de erro nova segue RFC 7807 (`type`, `title`, `status`, `detail`, `instance`, `code`, `timestamp`); exceções de domínio específicas; nenhum `except: pass` nem captura genérica sem relançar | ⏳ o handler global ainda não existe: use `HTTPException(detail=...)` (compatível, pois `detail` é campo do RFC) e nenhum formato de erro próprio; o handler é dívida TD-M5 | reviewer | o diff não cria nem altera resposta de erro nem tratamento de exceção |
| PY-5 | Resiliência de integrações | Chamada externa nova tem timeout, retry com backoff exponencial e jitter (só em operação idempotente), limite de taxa ou bulkhead quando houver risco de sobrecarga, e degradação graciosa (mensagem de fallback ou handoff humano) | ⏳ circuit breaker: sem biblioteca adotada, exija timeout + retry limitado + fallback; o breaker é dívida TD-M6 | reviewer | o diff não faz chamada de rede externa |
| PY-6 | Transactional Outbox | Escrita no banco + publicação de evento/mensagem assíncrona na mesma transação via outbox; proibido dual write | — | reviewer | o diff não publica evento nem mensagem assíncrona (hoje o projeto não tem fila) |
| FE-1 | TypeScript estrito e contratos | Zero `any`; `unknown` com type guard; toda resposta de API externa validada em runtime com Zod antes de ser usada | ⏳ `zod` ainda não está instalado (TD-A2): a primeira mudança que tocar `lib/api.ts` o adiciona (dependência gratuita, sem ADR) | reviewer | o diff não toca TypeScript |
| FE-2 | Feature Slices | Funcionalidade nova nasce em `src/features/<nome>/` (components, hooks, api, types, tests isolados); compartilhado vai para `src/lib` e `src/components`; legado migra só quando reescrito (TD-F3) | — | reviewer | o diff não cria funcionalidade no painel |
| FE-3 | Segurança no cliente | Sem `dangerouslySetInnerHTML` (se inevitável: DOMPurify com whitelist); credencial, JWT ou refresh token nunca em `localStorage`/`sessionStorage` (cookie HttpOnly, Secure, SameSite=Strict); preferência de UI (tema) pode usar `localStorage` | ⏳ o painel usa token estático no bundle (`VITE_API_TOKEN`), mitigado pelo Cloudflare Access (TD-A6: migrar para sessão por cookie HttpOnly); não amplie o uso | reviewer | o diff não toca `frontend/src` |
| FE-4 | CSP | Nenhum script ou estilo inline novo, nenhum `unsafe-inline`/`unsafe-eval`; CSP não é relaxada | ⏳ sem servidor para gerar nonce (Pages estático): CSP por `frontend/public/_headers` com `'self'`/hashes (TD-M7: o arquivo ainda não existe; não relaxe nada); o nonce dinâmico fica para depois | reviewer | o diff não toca HTML, cabeçalhos nem carregamento de scripts/estilos |
| FE-5 | Performance e FinOps | Rotas pesadas com `React.lazy` + `Suspense` e skeleton; nenhum chunk > 200 KB gzip; LCP < 2,5 s, INP < 200 ms, CLS < 0,1 medidos na tela alterada | ⏳ `size-limit` ainda não está no gate (TD-F1): o qa-tester mede o `dist/` (`gzip -c`) e as métricas via Playwright | qa | o diff não altera o que o painel carrega nem renderiza |
| FE-6 | Acessibilidade e datas (código) | WCAG 2.2 AA no mínimo (AAA onde viável): `label`, `alt`, papéis/ARIA corretos, foco gerenciado, estado nunca só por cor; datas armazenadas e trafegadas em UTC, convertidas só na exibição; estados carregando, vazio, erro e sucesso | — | reviewer | o diff não toca `frontend/src` |
| FE-7 | Acessibilidade e UX (execução) | Teclado completo e foco visível; contraste ≥ 4,5:1 (3:1 para texto grande e componentes) nos temas claro e escuro; 375, 768 e 1280 px sem rolagem horizontal; sem erro de console nem requisição 4xx/5xx no fluxo | — | qa | o diff não altera nada visível no painel |
| FE-8 | Design system | Só tokens de `tokens.css` (nada de hex/rgb/hsl, `opacity` ou cor padrão do Tailwind); componente reutilizável novo documentado em `docs/design-system.md` | ⏳ Storybook não adotado (TD-F2): a documentação no guia substitui a story até o ADR de Storybook | reviewer | o diff não toca `frontend/src` |
| SEC-1 | Zero segredos | Nenhum segredo, token, chave ou ID de terceiros em código, log, fixture, teste ou commit; `.env.example` só com placeholders | ⏳ o gitleaks ainda não está no CI (TD-A1): o reviewer varre o diff por padrões de segredo | reviewer | — |
| SEC-2 | Entrada e saída | Entrada validada nas fronteiras; SQL só por ORM/parametrizado; nada de `eval`/`exec`/`shell=True` com dado externo; saída escapada | — | reviewer | o diff não processa dado externo |
| SEC-3 | Autenticação e autorização | Endpoint novo é protegido (fail-closed) ou público por decisão justificada, com verificação de origem (HMAC) e limite de taxa; comparação de segredo em tempo constante; senha (se existir) com Argon2id; CORS restrito | ⏳ limite de taxa ainda não existe no backend: declare e teste o teto de tamanho/volume; o rate limit é dívida TD-A3 | reviewer | o diff não cria nem altera endpoint, autenticação ou CORS |
| SEC-4 | SAST | `bandit -r app` e Semgrep (workflow `semgrep.yml`) sem achado no diff | — (substituição permanente por custo, ADR-0001: bandit + Semgrep + ruff `S` no lugar do SonarQube; o gate roda bandit e ruff `S`, o Semgrep roda no CI) | reviewer | o diff não toca Python, TypeScript nem workflow |
| SEC-5 | SCA e cadeia de suprimentos | `pip-audit` e `npm audit --audit-level=high` sem achado; dependência nova justificada, com licença compatível e versão fixada pelo lockfile | ⏳ SBOM CycloneDX ainda não é gerado no CI (TD-A4): o inventário provisório são `requirements*.txt` e `package-lock.json`; nenhuma dependência sem versão fixada | qa | o diff não altera dependências |
| SEC-6 | LGPD / privacidade | Dado pessoal mínimo; telefone e conteúdo de conversa fora de log, console e URL; áudio bruto nunca persistido; pseudonimização quando o uso permitir; retenção/expurgo definidos para dado pessoal novo; criptografia em trânsito (TLS) e em repouso (o Neon cifra o disco; campo sensível novo avalia cifrar a coluna) | — | reviewer | o diff não trata dado pessoal |
| SEC-7 | Testes de segurança | Superfície de ataque nova ou alterada tem teste em `backend/tests/test_security.py` com payload malicioso; cada mitigação STRIDE tem teste | — | reviewer | o diff não cria nem altera superfície de ataque |
| AI-1 | Prompt injection | Texto do usuário nunca vira instrução de sistema: fica delimitado como dado; tamanho limitado antes do LLM; prompt de sistema não vaza; há teste com entrada adversária | — (substituição permanente por custo e peso, ADR-0001: delimitação, limite, filtro e teste adversário no lugar de NeMo Guardrails/Llama Guard) | reviewer | o diff não toca prompts nem chamada a LLM |
| AI-2 | Saída de LLM não confiável | Resposta do LLM validada (formato, tamanho) antes de persistir, enviar ou renderizar; nunca interpolada em SQL, HTML ou shell; ação com efeito só por allowlist | — | reviewer | o diff não consome saída de LLM |
| AI-3 | Dados e custo zero | Nenhum dado pessoal desnecessário enviado a LLM/terceiros; nenhum LLM ou serviço de tradução novo sem o teste de qualidade de `docs/decisoes-de-arquitetura.md` | — | reviewer | o diff não envia dado a terceiros |
| OBS-1 | Logs estruturados | Logs novos via `logging` do módulo, estruturados (campos, não texto solto), sem PII, no nível certo; erros com contexto e sem stack para o cliente | ⏳ JSON com `correlation_id`/`trace_id`/`span_id` e filtro de PII dependem do middleware de observabilidade (TD-O1): use `extra={...}` para que ele passe a cobrir | reviewer | o diff não adiciona nem altera log |
| OBS-2 | Métricas e tracing | Endpoint ou integração nova expõe métricas RED (Rate, Errors, Duration), os recursos que consome entram nas métricas USE (Utilization, Saturation, Errors) e o contexto W3C é propagado nas chamadas HTTP de saída | ⏳ OpenTelemetry/Prometheus (RED e USE) ainda não existem (TD-O1): não degrade a observabilidade atual e mantenha `/health` fiel | reviewer | o diff não cria endpoint nem integração |
| OBS-3 | Resiliência validada | Queda simulada da dependência (Groq, WhatsApp, banco) resulta em degradação graciosa, sem 5xx para o usuário final nem perda de mensagem | ⏳ Chaos Engineering em staging não existe (TD-O3): a simulação é feita por teste automatizado ou exploratório local | qa | o diff não toca integração externa nem tratamento de falha |
| OBS-4 | SLO e continuidade (ISO 20000/22301) | Mudança em produção, dados ou deploy declara o impacto nos SLOs (disponibilidade, latência) e mantém a recuperação dentro de RPO/RTO < 15 min (backup/PITR do banco, rollback de revisão do Cloud Run) | ⏳ SLO/SLA/SLI e o plano de recuperação de desastres ainda não estão definidos (TD-O2): descreva o impacto e o rollback no PR | reviewer | o diff não altera produção, dados nem deploy |
| DATA-1 | Concorrência e idempotência | Leitura-modificação-escrita de estado compartilhado usa `SELECT ... FOR UPDATE` ou controle otimista por versão; operação repetida (retentativa de webhook) é idempotente | — | reviewer | o diff não modifica estado compartilhado |
| DATA-2 | Migrações e consultas | Migração Alembic reversível, sem perda de dados e testada; índices para consultas novas; sem N+1 nem I/O dentro de laço | — | reviewer | o diff não altera modelo nem consulta |
| DATA-3 | Trilha de auditoria | Criação, alteração e exclusão de dado sensível registra quem, quando, IP/dispositivo, estado anterior e novo, em armazenamento append-only com encadeamento criptográfico (hash chain) que impede alteração, inclusive por administradores | ⏳ a tabela de auditoria e o hash chain não existem (TD-A5): a mutação nova registra o evento em log estruturado com todos esses campos | reviewer | o diff não muta dado sensível |
| DATA-4 | Multi-tenant / RLS | Isolamento por cliente com Row-Level Security no PostgreSQL | — | reviewer | o sistema é single-tenant (ADR-0001); passa a valer no dia em que surgir um segundo cliente |
| INF-1 | Docker hardening | Dockerfile multi-stage, base mínima, `USER` não-privilegiado, sem utilitários de shell desnecessários na imagem final | ⏳ o `Dockerfile` atual é single-stage em `python:3.11-slim` (TD-I1): linhas novas seguem a regra, sem piorar | reviewer | o diff não toca Dockerfile nem imagem |
| INF-2 | Imagem e proveniência | Imagem sem CVE crítica/alta (Trivy/Grype); artefato assinado (Cosign) com proveniência | ⏳ não há varredura de CVE nem assinatura no deploy (TD-I2): o `Dockerfile` do diff fixa a base (tag ou digest), não adiciona pacote de SO sem necessidade e `pip-audit` está limpo | qa | o diff não toca build nem deploy |
| INF-3 | CI/CD e IaC | Workflows com `permissions` mínimas, actions em versão fixada, sem segredo em log; Dockerfile/workflows sem má configuração (Checkov) | ⏳ Checkov não está no CI (TD-I3): revisão manual dos mesmos pontos | reviewer | o diff não toca `.github/`, Dockerfile nem IaC |
| INF-4 | FinOps | Custo zero mantido: nenhuma dependência ou serviço pago; limites de CPU/memória/concorrência/instâncias declarados no deploy | — | reviewer | o diff não altera deploy, dependências nem consumo de recursos |
| INF-5 | Deploy sem downtime | Mudança de risco usa rollout gradual (revisões do Cloud Run com divisão de tráfego) e flag de desligamento; rollback automático se 5xx > 0,1% nos primeiros 10 min | ⏳ rollout gradual e flags ainda não configurados (TD-I4): descreva o plano de rollback no PR | qa | o diff não altera comportamento em produção nem o deploy |
| INF-6 | Zero Trust / mTLS | Comunicação entre serviços autenticada e criptografada (mTLS, SPIFFE) | — | reviewer | há um único serviço, com TLS no Cloud Run (ADR-0001); passa a valer com o segundo serviço |
| TEST-1 | Testes do código novo | Todo código novo tem teste de comportamento (Arrange-Act-Assert, bordas e erros, sem assert trivial); bug corrigido tem teste de regressão que falhava antes | — | reviewer | — |
| TEST-2 | Eficácia dos testes | Lógica crítica nova (HMAC, matcher, regras de negócio) resiste a mutação: quebrar a linha faz algum teste falhar | ⏳ mutmut/Stryker fora do gate (TD-T1): o reviewer faz a "mutação mental" e cita quais testes matariam qual mutante | reviewer | o diff não altera lógica de decisão |
| TEST-3 | E2E e exploratório | Mudança visível tem spec Playwright; a suíte E2E inteira passa; o exploratório cobre caminho feliz, validações, bordas e estados vazio/carregando/erro | ⏳ DAST com OWASP ZAP em staging não existe (TD-T2): o `/security-check` cobre o pentest local | qa | o diff não altera nada visível nem endpoint |
| DOC-1 | Documentação | `README`, `docs/`, guia do design system, `tech-debt.md`, ADR e docstrings Google em pt-BR refletem a mudança; comentários explicam o porquê | — | reviewer | — |
