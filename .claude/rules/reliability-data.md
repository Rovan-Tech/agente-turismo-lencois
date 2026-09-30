---
paths:
  - "backend/app/**"
  - "backend/alembic/**"
  - "backend/tests/**"
---

# Confiabilidade (SRE), observabilidade e dados

Itens do checklist: `OBS-1`..`OBS-3`, `DATA-1`..`DATA-4`, `PY-5`, `PY-6`. A base de observabilidade
(OpenTelemetry, métricas, auditoria em hash chain) ainda não existe: ver _Conformidade com o
Manual V5_ em `docs/tech-debt.md`. O requisito vale como o checklist descreve na coluna ⏳.

## Logs (`OBS-1`)
- `logging` do módulo (`logger = logging.getLogger(__name__)`), nunca `print`. Campos estruturados
  em `extra={...}` (ex.: `extra={"event": "webhook_rejected", "reason": "bad_signature"}`), não
  texto solto com f-string.
- **Nunca** PII: telefone, conteúdo de conversa, token, áudio. Mascare (`****1234`) se precisar
  correlacionar. O alvo é JSON com `correlation_id`, `trace_id` e `span_id` (middleware: TD-O1).
- Erro devolvido ao cliente não tem stack trace; o log tem o contexto.

## Métricas e tracing (`OBS-2`)
- Endpoint/integração nova expõe RED (Rate, Errors, Duration) e os recursos entram em USE
  (Utilization, Saturation, Errors: CPU, memória e instâncias do Cloud Run) quando o coletor existir; propague o
  contexto W3C (`traceparent`) nas chamadas HTTP de saída. `/health` reflete o estado real.

## Resiliência (`PY-5`, `OBS-3`)
- Timeout em toda chamada externa; retry com backoff exponencial **e jitter** só em operação
  idempotente; bulkhead/limite de concorrência para integrações lentas; circuit breaker quando a
  biblioteca for adotada (TD-M6); fallback que nunca deixa o turista sem resposta.
- Teste simulando a queda de cada dependência (Groq, WhatsApp, banco).

## SLO e continuidade (`OBS-4`)
- Mudança em produção, dados ou deploy declara o impacto nos SLOs (disponibilidade, latência) e
  preserva a recuperação: RPO/RTO < 15 min (backup/PITR do Neon, rollback de revisão do Cloud Run).
  SLO/SLA/SLI e o plano de desastre formais são dívida (TD-O2); descreva o rollback no PR.

## Dados (`DATA-1`..`DATA-4`)
- **Concorrência**: read-modify-write de estado compartilhado usa `with_for_update()` ou coluna de
  versão (controle otimista). O webhook é **idempotente** (id da mensagem da Meta): repetir não
  duplica efeito.
- **Migrações** Alembic reversíveis (`downgrade` de verdade), sem perda de dados, testadas; índice
  para consulta nova; sem N+1 nem I/O em laço.
- **Auditoria**: mutação de dado sensível registra quem, quando, IP/dispositivo, estado anterior e
  novo, append-only (tabela + hash chain: TD-A5; até lá, log estruturado com esses campos).
- **Multi-tenant/RLS**: N/A enquanto for single-tenant (ADR-0001); obrigatório assim que existir um
  segundo cliente.
- **Datas em UTC** no banco e na API (`datetime.now(UTC)`); nunca `datetime.now()` ingênuo.
