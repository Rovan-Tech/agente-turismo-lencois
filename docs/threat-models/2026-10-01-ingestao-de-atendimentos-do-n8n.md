# Threat model: endpoint de entrada para o n8n registrar atendimentos

- **Data:** 2026-10-01
- **Escopo:** `POST /api/ingest/atendimentos` (ADR-0005, etapa 2a): o n8n envia a mensagem do
  turista e a resposta já enviada, e o backend grava conversa e mensagens para o painel. Fica de
  fora: transcrição de áudio (2b), filtro de candidatos do catálogo (2c), o fluxo do n8n em si
  (`2026-10-01-n8n-gemini-whatsapp.md`) e o painel de leitura.
- **Dados sensíveis:** telefone, texto e nome do perfil do WhatsApp do turista (LGPD); resposta gerada pelo modelo; o
  `INGEST_API_TOKEN` (nova credencial de escrita); `whatsapp_message_id` (id da Meta).
- **Fronteiras de confiança:** n8n Cloud → backend público (Internet, token); backend → banco. O
  conteúdo de `texto` e `resposta` é **dado não confiável** (vem do turista e do LLM) e é exibido no
  painel.

## Diagrama de fluxo (texto)

```
turista --> Meta --> n8n --(responde no WhatsApp)--> turista
n8n --POST /api/ingest/atendimentos, Bearer INGEST_API_TOKEN, JSON ≤ 16 KiB--> backend (Cloud Run, público)
backend: token (tempo constante, fail-closed) -> schema estrito -> lista permitida do passeio
       -> uma transação: conversa + mensagem do turista (índice único do id) + resposta
       --> Neon --> painel (GET /api/conversations, token do painel, texto exibido sem HTML)
resposta ao n8n: {"status": "criado|duplicado", "conversa_id": …}  (sem telefone nem texto)
```

## Ameaças (STRIDE)

Testes de segurança ficam em `backend/tests/test_ingest_security.py`: o `test_security.py` tem 272
linhas e somar os cerca de 250 deste endpoint passaria do limite de 400 por módulo, então é um
desvio consciente do caminho literal da regra de segurança (o helper de comparação do token tem seu
teste unitário em `test_security.py`), os de comportamento em `backend/tests/test_ingest.py`, o
expurgo em `backend/tests/test_purge_conversations.py` e a regra dos tokens em
`backend/tests/test_config.py`. Todos foram escritos antes do código (TDD).

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | Chamada sem credencial ou com token errado cria conversas falsas no painel | Painel poluído, atendimento falso, dado pessoal inventado | `Authorization: Bearer` obrigatório, comparação com `hmac.compare_digest`, 401 sem gravar nada | `test_ingest_rejects_invalid_credentials_without_writing[no_token|wrong_token|basic_scheme|bearer_without_value|no_scheme|lowercase_scheme]` | Nenhum |
| **S**poofing | `INGEST_API_TOKEN` não configurado e a rota aceita qualquer coisa (inclusive `Bearer ` vazio) | Escrita aberta na Internet | Fail-closed: token vazio = 401 sempre | `test_ingest_with_unset_token_returns_401_even_for_empty_bearer` | Nenhum |
| **S**poofing | Usar o token do painel (que está no bundle público) para escrever | Qualquer visitante do site forja conversas | Token próprio e distinto; o do painel é recusado no ingest | `test_ingest_rejects_invalid_credentials_without_writing[dashboard_token]` | Nenhum, desde que os dois valores sejam diferentes (checagem na configuração, ver abaixo) |
| **S**poofing | `INGEST_API_TOKEN` igual a `DASHBOARD_API_TOKEN` por engano | Anula a mitigação acima | A aplicação **recusa subir** (ou o ingest responde 401) se os dois forem iguais | `test_settings_reject_ingest_token_equal_to_dashboard_token` | Baixo |
| **S**poofing | Cabeçalho `Authorization` com caractere não-ASCII derruba a comparação do token (`TypeError`) e vira 500 sem credencial | Erro 500 e traceback provocados por qualquer pessoa; ruído no critério de 5xx do deploy (também afetava `/api/tours`) | A comparação é feita em bytes (`hmac.compare_digest` com `encode()`): cabeçalho inválido é 401 | `test_non_ascii_authorization_returns_401_instead_of_crashing[ingest|conversations|tours]`, `test_bearer_token_with_non_ascii_characters_is_rejected_without_raising` | Nenhum |
| **S**poofing | Telefone arbitrário no corpo: quem tem o token grava conversa em nome de qualquer número | Conversa atribuída a terceiro | O n8n já validou a assinatura da Meta e envia o `from` do evento; o backend só aceita formato válido (8 a 15 dígitos). Quem tem o token é de confiança | `test_ingest_rejects_invalid_payloads_without_writing[phone_with_plus|phone_with_space|phone_letters|phone_too_short|phone_too_long|phone_empty|phone_int]` | Médio: depende do sigilo do token (ver vazamento) |
| **T**ampering | Campos extras, tipos trocados, textos gigantes, `idioma` fora de `pt|en|es` | Dado inválido no banco, lentidão | Pydantic estrito com `extra="forbid"`, limites (`texto` e `resposta` até 4096, id até 128, corpo até 16 KiB), `idioma` restrito | `test_ingest_rejects_invalid_payloads_without_writing` (campo extra, tipos trocados, textos acima do limite, idioma fora de `pt|en|es`), `test_ingest_rejects_a_payload_missing_any_field`, `test_ingest_accepts_the_largest_valid_fields`, `test_ingest_rejects_unreadable_bodies_without_writing[body_over_16_kib]` | Nenhum |
| **T**ampering | `passeio_sugerido_id` inventado, inativo ou com texto de injeção SQL | FK inválida, 500, sugestão de passeio fora do catálogo | Só vale se existir e estiver ativo; senão vira `null` e o atendimento é gravado; consulta parametrizada | `test_ingest_drops_a_suggested_tour_that_is_not_an_active_catalog_entry[unknown|inactive|sql_payload]` | Baixo |
| **T**ampering | `texto` ou `resposta` com HTML/script (XSS armazenado) | Script no navegador da equipe | O backend grava o texto como veio e o devolve só como JSON; o painel exibe como texto (React, sem `dangerouslySetInnerHTML`, proibido pelo gate) | `test_ingest_stores_markup_verbatim_and_returns_it_as_json` (também confere que a resposta só tem `status` e `conversa_id`); no painel, `MessageBubble shows markup in a message as plain text, never as elements` (Vitest) | Baixo |
| **T**ampering | O chamador tenta mudar o estado da conversa além do permitido (marcar `resolvida`, rebaixar um "precisa de atenção", mexer em passeios ou reservas) | Atendimento encerrado ou pedido de humano apagado sem ninguém atender; catálogo adulterado | O contrato só tem `precisa_atencao_humana` (booleano): `true` escala para `precisa_atencao`; `false` não muda o status. A marca só sai quando uma pessoa resolve no painel. Nenhum campo chega a `resolvida`, passeios ou reservas | `test_ingest_status_only_escalates_and_never_resolves[stays_open|escalates|false_does_not_clear|stays_escalated]`, `test_ingest_does_not_touch_the_tours` | Baixo |
| **T**ampering | A saída do LLM controla algo além de texto | Ação indevida a partir de prompt injection | A saída só preenche `resposta`, `idioma`, `passeio_sugerido_id` (lista permitida) e um booleano; nada é executado (OWASP LLM01/02) | Cobertos pelos testes de passeio e de marcação acima | Médio: sem guardrail dedicado de injeção (aceite do 0004, pendente) |
| **R**epudiation | Não dá para saber o que o n8n gravou nem quando | Disputa sem prova | Cada mensagem tem `created_at` e `whatsapp_message_id`; o log registra o resultado de cada chamada sem dado pessoal | `test_ingest_logs_the_outcome_without_personal_data`, `test_app_logger_emits_info_with_its_own_handler` (o uvicorn só configura os próprios loggers; `app.main` liga o do `app`) | Médio: sem auditoria append-only com hash (TD-A5) |
| **R**epudiation | Repetir uma chamada capturada | Mensagem duplicada, contagem errada | Idempotência pelo índice único: repetir devolve `duplicado` com 200 e não grava | `test_ingest_replay_returns_duplicate_and_writes_nothing` | Nenhum |
| **I**nformation disclosure | A resposta ou o erro ecoam telefone, texto ou token | Dado pessoal nas execuções do n8n (retenção indefinida, TD-N5) | Resposta só com `status` e `conversa_id`; o 422 desta rota **remove o campo `input`** do detalhe | `test_ingest_validation_error_does_not_echo_submitted_values` | Baixo |
| **I**nformation disclosure | Telefone, texto ou token nos logs do Cloud Run, ou token na URL | Vazamento de dado pessoal e de credencial (hoje o `hub.verify_token` do webhook aparece nos logs porque vai na query) | Token só no cabeçalho; nenhuma mensagem de log com telefone, texto, token ou id da Meta | `test_ingest_never_logs_phone_text_or_token` (caplog), `test_ingest_returns_401_before_reading_the_body_or_the_query[token_in_query_string]` | Baixo |
| **I**nformation disclosure | `GET /api/ingest/catalogo` (leitura do catálogo pelo n8n) expõe dado interno ou pessoal | Catálogo de passeios e preços visível a quem tiver o token | Mesmo portão da gravação (`INGEST_API_TOKEN`, fail-closed); devolve só passeios **ativos** e só os campos do catálogo (os mesmos que iam ao LLM), sem capacidade, estado nem telefone; nenhum dado de turista | `test_ingest_catalog_lists_only_active_tours_with_the_catalog_fields`, `test_ingest_rejects_invalid_credentials_without_writing[read_catalog x credenciais inválidas]` | Baixo: o catálogo é público por natureza (é o que o bot diz aos turistas) |
| **I**nformation disclosure | Falha do banco no meio da gravação: o texto da exceção do SQLAlchemy traz os parâmetros do SQL (telefone e texto do turista) e o uvicorn o grava no log de erro | Dado pessoal no log do Cloud Run | `hide_parameters=True` no engine; a rota captura `SQLAlchemyError`, loga só o nome do tipo (sem traceback) e devolve 503 (o n8n tenta de novo, e repetir é seguro); NUL é barrado na entrada (o Postgres o recusaria) | `test_engine_hides_sql_parameters_from_error_messages`, `test_ingest_database_failure_returns_503_without_logging_personal_data`, `test_ingest_rejects_invalid_payloads_without_writing[texto_with_nul|resposta_with_nul|id_with_nul|tour_with_nul]` | Baixo |
| **I**nformation disclosure | Telefone e texto do turista guardados sem prazo (LGPD) | Dado pessoal retido além do necessário | Retenção de **90 dias** (decisão do Patrick, mesmo valor de `phone_retention_days`): rotina que apaga conversas inativas há mais de 90 dias **com as mensagens**, entregue junto com o endpoint | `test_purge_deletes_conversations_inactive_over_retention_with_their_messages`, `test_purge_keeps_conversations_with_recent_activity`, `test_purge_is_idempotent`, `test_purge_deletes_old_conversations_in_any_status`, `test_purge_keeps_a_conversation_that_got_a_legacy_webhook_message_today` (o webhook antigo também marca a atividade), `test_main_purges_with_the_configured_retention` | Médio: a cópia nas execuções do n8n segue sem retenção (TD-N5, Alta, fora deste escopo) |
| **I**nformation disclosure | `INGEST_API_TOKEN` vaza (credencial do n8n, histórico do GitHub, log) | Escrita aberta na rota | Valor forte e aleatório; só no segredo do GitHub, no Cloud Run e na credencial do n8n; varredura de segredos do CI; rotação, não só apagar. Interruptor: apagar a variável faz a rota responder 401 | `test_ingest_with_unset_token_returns_401_even_for_empty_bearer` (interruptor); gitleaks no CI | Médio: sem expiração automática |
| **D**enial of service | Inundação de chamadas ou corpos grandes enchem o banco e consomem a cota gratuita | Banco cheio, custo | Teto de 16 KiB por corpo e limites por campo; só quem tem o token chega ao banco | `test_ingest_body_limit_holds_at_the_boundary_with_and_without_content_length` (16 KiB passa e 16 KiB + 1 dá 413, com `Content-Length` e em `chunked`), `test_ingest_rejects_unreadable_bodies_without_writing[body_over_16_kib]` | **Médio:** sem limite de taxa (TD-A3, Alta); aceitar com decisão do Patrick |
| **D**enial of service | `CONVERSATION_RETENTION_DAYS` com 0 ou negativo: o corte cai no futuro e o expurgo apaga todas as conversas | Perda total do histórico por erro de configuração | O valor tem mínimo de 1 dia | `test_conversation_retention_must_be_at_least_one_day[0|-1]` | Baixo |
| **D**enial of service | Duas chamadas simultâneas com o mesmo id geram erro 500 ou linhas duplicadas | Atendimento duplicado no painel ou falha para o n8n | O índice único barra; quem perde a corrida recebe `duplicado` (200) depois do `rollback` | `test_ingest_concurrent_same_message_id_writes_once` | Nenhum |
| **D**enial of service | Backend fora do ar ou lento (Neon frio, conexão fechada) | Atendimento respondido e não registrado | 3 tentativas no n8n, seguras por serem idempotentes; falha do ingest **não** dispara a contingência (evita a mensagem duplicada ao turista); `pool_pre_ping` já em produção (PR #49) | `test_ingest_retry_after_failure_writes_once` | **Médio:** se as 3 falharem, o registro se perde (aceito na demo; ver o ADR) |
| **I**nformation disclosure | O nome do perfil do WhatsApp (`cliente_nome`, adendo de 2026-10-03 do ADR-0005) vaza para log, erro, prompt do Gemini ou resposta do n8n | Dado pessoal em terceiros e nos logs do Cloud Run | Campo opcional só gravado no banco e devolvido ao painel; o 422 não ecoa valores; o fluxo do n8n não o inclui no que vai ao modelo; apagado com a conversa (90 dias) | `test_the_name_is_never_logged_by_the_ingest_routes`, `test_the_name_is_never_logged_by_the_webhook`, `test_a_database_failure_does_not_log_or_return_the_name`, `test_ingest_rejects_an_invalid_name_without_echoing_it`, `test_the_name_never_reaches_the_llm_prompt_or_the_tourist_reply`, `test_the_profile_name_never_reaches_the_model_prompt` | Baixo: a cópia nas execuções do n8n segue sem retenção (TD-N5) |
| **E**levation of privilege | O token de escrita serve para ler conversas e telefones, ou o do painel serve para escrever | Leitura de dado pessoal por quem só deveria gravar | Tokens separados; o do ingest não abre `/api/conversations` nem `/api/tours`; o do painel não abre o ingest | `test_ingest_token_is_rejected_by_dashboard_routes`, `test_ingest_rejects_invalid_credentials_without_writing[dashboard_token]` | Nenhum |
| **E**levation of privilege | Fabricar um atendimento para fazer a equipe agir (por exemplo, "precisa de atenção" falso) | Tempo da equipe, confusão | O pior efeito é uma conversa marcada como "precisa de atenção"; nenhum passo automático depende disso; exige o token | n/a | Baixo |

## Decisões

Tomadas pelo Patrick em 2026-10-01:

1. **Retenção:** 90 dias para o telefone e o texto das conversas, o mesmo valor das reservas.
2. **Status:** "precisa de atenção" só quando o bot não tem resposta ou está em dúvida (um atendente
   responde pela plataforma). A rota só escala e nunca rebaixa; a marca sai quando uma pessoa
   resolve no painel. Observação: o painel hoje não envia mensagens; esse envio seria outra
   funcionalidade, com ADR e threat model próprios.

3. **Nome da rota:** `/api/ingest/atendimentos`, aprovado com o "pode seguir" de 2026-10-01.

## Riscos aceitos

- Ausência de limite de taxa na rota (TD-A3): só o n8n tem o token e há teto por chamada.
  **Aceito pelo Patrick em 2026-10-01 ("pode seguir").**
- Registro perdido se o backend falhar nas 3 tentativas: o conteúdo continua nas execuções do n8n.
  **Aceito pelo Patrick em 2026-10-01 ("pode seguir").**
- Resposta duplicada ao turista por reenvio da Meta (TD-N1) continua; este endpoint só evita o
  registro duplicado. **Aceito pelo Patrick em 2026-10-01 ("pode seguir").**
- Ausência de guardrail dedicado contra injeção de prompt: já listada no threat model do n8n.
  **Aceito pelo Patrick em 2026-10-01 ("pode seguir").**
- A retenção das conversas no backend está resolvida pela decisão 1 (rotina de expurgo na mesma
  entrega). A cópia do telefone e do texto nas execuções do n8n Cloud **continua sem prazo** (TD-N5,
  Alta, fora deste escopo) e **não é aceita**: precisa ser configurada no n8n antes de ampliar o
  público.
