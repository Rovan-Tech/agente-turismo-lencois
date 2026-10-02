# Threat model: agendamento com pagamento simulado

- **Data:** 2026-09-30
- **Escopo:** novo modelo `Booking` (passeio, data, pessoas, forma de pagamento, status, telefone
  opcional), campo `capacidade_diaria` no `Tour`, e os endpoints `GET /api/tours/{id}/agenda`,
  `GET /api/tours/{id}/agendamentos`, `POST /api/tours/{id}/agendamentos`. Fica de fora: qualquer
  integração real de gateway de pagamento (não existe e não vai existir aqui — é simulação pro
  portfólio) e a tela de catálogo "vagas por dia" (tarefa separada, branch `feat/tours-vagas-por-dia`,
  que só consome esses mesmos dados).
- **Dados sensíveis:** telefone (opcional, LGPD); número de pessoas e forma de pagamento não são
  dado de pagamento real (não há número de cartão, CVV nem dado bancário — é só um rótulo de
  simulação), então não há escopo de PCI-DSS aqui.
- **Fronteiras de confiança:** painel (navegador, atendente da agência) → API autenticada (`require_dashboard_auth`:
  token fixo em `Authorization: Bearer` ou, com o login do painel, JWT do Cloudflare Access em
  cookie, conforme `PANEL_AUTH_MODE`, ADR-0006) → banco. Não há ator externo (turista) nesta funcionalidade.

## Diagrama de fluxo (texto)

```
atendente --auth--> GET /api/tours/{id}/agenda?mes=... --> banco (SELECT agregando bookings pagos)
atendente --auth--> POST /api/tours/{id}/agendamentos --> banco (lock na linha do Tour,
  reconta vagas na mesma transação, grava Booking com status_pagamento=pago)
atendente --auth--> GET /api/tours/{id}/agendamentos?data=... --> banco --> lista com telefone
  (só pro atendente autenticado, nunca pro LLM, nunca em log)
```

## Ameaças (STRIDE)

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | Chamar os endpoints novos sem o token do painel | Criar/ler agendamentos sem autorização | Mesma dependência `require_dashboard_auth` (fail-closed) de todos os endpoints do painel, aplicada ao router inteiro | `test_security.py::test_booking_endpoints_require_dashboard_token` | Com o token fixo (modos `token`/`both`) segue um segredo compartilhado da agência; no modo `access` cada pessoa é validada pelo JWT do Access (dívida TD-A6, pré-existente) |
| **T**ampering | CSRF: com a sessão do Access em cookie, outra página faz o navegador do atendente enviar `POST /agendamentos` | Agendamento criado em nome do atendente | A mutação exige o cabeçalho `X-Panel-Request: 1` (que página de terceiro não consegue enviar); o frontend manda o cabeçalho no `createBooking` pelo mesmo `sendJson` das demais mutações | `test_panel_modes.py::test_panel_auth_mutation_without_the_exact_panel_header_is_rejected[post_booking]`, `test_panel_modes.py::test_panel_auth_mutation_with_panel_header_reaches_the_route[post_booking]`, `api.test.ts` ("createBooking sends a POST…") | Nenhum |
| **T**ampering | `pessoas` negativo, zero ou absurdamente grande | Vaga negativa, estouro de capacidade, custo de processamento | `Field(gt=0, le=50)` no schema de entrada | `test_bookings_api.py::test_create_booking_rejects_invalid_payloads` (casos `pessoas-zero`, `pessoas-negativo`, `pessoas-acima-do-teto`) | Nenhum |
| **T**ampering | Dois agendamentos quase simultâneos somam mais pessoas do que a capacidade do dia (TOCTOU) | Overbooking | `create_booking` abre transação, faz `SELECT ... FOR UPDATE` direto na linha do `Tour` (consulta própria, não `tour_catalog.get_tour`), reconta as vagas pagas daquele dia dentro da mesma transação e só então decide; nenhuma leitura de capacidade fora da transação | `test_booking_service.py::test_create_booking_locks_the_tour_row_for_update` (prova que a consulta pede o lock), `test_booking_service.py::test_create_booking_rejects_when_second_booking_would_exceed_capacity` (prova a recontagem) | SQLite (dev/testes) não aplica lock real — sem conexões concorrentes de verdade em teste sequencial, o cenário de corrida completa não é testável localmente; em produção (Postgres) o lock é efetivo. Proposto; aguarda o aceite do Patrick (ver Riscos aceitos). |
| **T**ampering | Cliente manda `status_pagamento` no corpo da requisição tentando forjar "pago" sem passar pela simulação, ou um campo desconhecido | Agendamento criado com estado indevido | O schema de entrada (`BookingCreate`) não tem campo `status_pagamento` — o backend sempre define `PAGO` (é a simulação de "pagamento aprovado"); `ConfigDict(extra="forbid")` rejeita qualquer campo a mais | `test_security.py::test_booking_rejects_forged_payment_status`, `test_bookings_api.py::test_create_booking_rejects_invalid_payloads` (caso `campo-desconhecido`), `test_bookings_api.py::test_create_booking_always_persists_as_paid` | Nenhum |
| **T**ampering | `tour_id` de um passeio inexistente ou desativado | Agendamento órfão ou para um passeio que a agência tirou do catálogo | `create_booking` faz sua própria busca (com lock) e checa `ativo` antes de criar; `get_monthly_occupancy` e `get_day_bookings` usam `tour_catalog.get_tour` pra validar existência antes de responder | `test_booking_service.py::test_create_booking_rejects_unknown_tour`, `test_booking_service.py::test_create_booking_rejects_inactive_tour`, `test_booking_service.py::test_get_day_bookings_rejects_unknown_tour`, `test_bookings_api.py::test_list_day_bookings_unknown_tour_returns_404` | Nenhum |
| **R**epudiation | Não saber quem/quando criou um agendamento, nem a ocupação antes/depois | Disputa sobre vaga vendida | `created_at` automático; log estruturado na criação com `booking_id`, `tour_id`, `data`, `pessoas`, `forma_pagamento`, `ocupadas_antes`, `ocupadas_depois`, `ator` (o `sub` da pessoa no JWT do Access; "dashboard" só com o token fixo), `ip` e `user_agent` da requisição — nunca telefone | `test_booking_service.py::test_create_booking_logs_structured_event_without_phone`, `test_panel_modes.py::test_booking_audit_log_records_the_person_from_the_access_jwt`, `test_panel_modes.py::test_booking_audit_log_falls_back_to_dashboard_with_the_static_token` | Com o token fixo (modos `token`/`both`) o `ator` é só "dashboard", sem saber qual atendente; no modo `access` a pessoa fica registrada. `ip` reflete o proxy do Cloud Run, não o cliente final, até o uvicorn ganhar `--forwarded-allow-ips` (dívida de infra, ver riscos aceitos) |
| **I**nformation disclosure | Telefone vazar em log, erro ou URL | Dado pessoal exposto | Telefone nunca entra em log estruturado nem em mensagem de exceção; só é exposto no corpo de `GET /agendamentos`, atrás de auth | `test_security.py::test_booking_phone_never_appears_in_logs` | Sem cifragem adicional da coluna nem expurgo automático — ver seção LGPD abaixo. **Proposto; aguarda o aceite do Patrick.** |
| **D**enial of service | Spam de agendamentos (válidos, um por um) esgotando vagas de propósito | Indisponibilidade de vagas reais | Teto de `pessoas` por requisição (`le=50`) como teto de volume provisório | `test_bookings_api.py::test_create_booking_rejects_invalid_payloads` (caso `pessoas-acima-do-teto`) | Sem limite de taxa por token/IP (dívida TD-A3, pré-existente, fora do escopo) |
| **E**levation of privilege | Resposta de erro ou endpoint dispara alguma ação não solicitada (ex.: desativar o passeio) | Ação sem autorização | Os endpoints novos só leem/criam `Booking`; nenhum deles muta `Tour` além de leitura de `capacidade_diaria` | `test_bookings_api.py::test_create_booking_does_not_mutate_tour_fields` | Nenhum |

## LGPD — retenção e cifragem do telefone (SEC-6)

- **Minimização**: `telefone` é opcional; o atendente só o preenche quando precisa retornar
  contato ao turista. Nenhum outro dado pessoal novo (nome, e-mail, documento) é coletado.
- **Retenção/expurgo**: ainda não há automação para `bookings` (as conversas já têm o
  expurgo `app/purge_conversations.py`, ADR-0005), mas o prazo já fica definido aqui: anonimizar
  `telefone` (sobrescrever com `NULL`) **90 dias** após `data` do passeio — tempo suficiente para
  disputa sobre a vaga (Repudiation acima) sem reter o contato além do necessário. A rotina (ex.:
  job agendado) é a dívida registrada em `docs/tech-debt.md` (`TD-A7`), não o prazo em si.
- **Cifragem em repouso**: avaliado e **não aplicado** nesta tarefa — o Neon (produção) já cifra o
  disco inteiro (cifragem at-rest do provedor); cifrar a coluna também exigiria gerenciar chave e
  rotação, desproporcional para um campo opcional de baixo risco (telefone, não documento/pagamento
  real). Mesma decisão já implícita para `conversations.whatsapp_phone`. **Proposto; aguarda o
  aceite do Patrick.**
- **Trânsito**: TLS do Cloud Run/Neon, já coberto pela infra existente (nenhuma mudança aqui).

## Impacto em produção e rollback (OBS-4)

- A migração `0005` é aditiva: `capacidade_diaria` entra com `server_default="30"` (nenhuma linha
  existente quebra) e `bookings` é uma tabela nova (nenhum dado existente é tocado). Sem
  indisponibilidade esperada durante o deploy.
- **Rollback**: `alembic downgrade 0004` remove a tabela `bookings` (perde os agendamentos
  simulados criados desde o deploy) e a coluna `capacidade_diaria`, sem tocar nas colunas de
  atendimento humano da migração `0004` (nunca use `downgrade 0003` para isso: apagaria o estado de
  atendimento das conversas). Como é ambiente de portfólio
  sem agendamentos reais em produção, o risco do downgrade é aceitável; uma rotação de revisão do
  Cloud Run sozinha (sem downgrade de schema) já é suficiente pra reverter o código, já que a
  coluna/tabela novas são apenas aditivas e não quebram o schema anterior.
- Sem SLO formal definido ainda para o painel (TD-O2, pré-existente); esta mudança não altera
  disponibilidade nem latência dos endpoints existentes (`/api/tours`, `/api/conversations`).

## Riscos aceitos

- Condição de corrida real (duas conexões concorrentes de verdade) só é mitigada em produção
  (Postgres com `FOR UPDATE`); em SQLite (dev e job SQLite do CI) o teste prova a lógica de recontagem, não o lock
  físico. **Proposto; aguarda o aceite do Patrick.**
- Sem rate limiting por token/IP nos endpoints novos (TD-A3, dívida já registrada antes desta
  tarefa). **Proposto; aguarda o aceite do Patrick.**
- Sem cifragem adicional da coluna `telefone` nem automação do expurgo aos 90 dias ainda
  implementada (ver seção LGPD acima, `TD-A7`). **Proposto; aguarda o aceite do Patrick.**
- `ip` da trilha de auditoria (DATA-3) reflete o proxy do Cloud Run, não o cliente final, enquanto
  o uvicorn não roda com `--forwarded-allow-ips` configurado (dívida de infra, fora do escopo desta
  tarefa — nenhum endpoint do painel propaga IP real hoje). **Proposto; aguarda o aceite do
  Patrick.**
