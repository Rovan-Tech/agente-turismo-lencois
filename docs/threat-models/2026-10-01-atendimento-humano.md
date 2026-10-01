# Threat model: atendimento humano pelo painel (assumir a conversa e responder)

- **Data:** 2026-10-01
- **Escopo:** assumir e devolver a conversa, enviar mensagem de WhatsApp pelo painel como a agência, a
  consulta do n8n sobre o estado da conversa e a gravação das mensagens do atendente (ADR-0008). Fica
  de fora: notificação em tempo real, papéis por pessoa e modelos de mensagem da Meta (fora da
  janela de 24 h).
- **Dados sensíveis:** telefone e texto de turistas (LGPD); o `WHATSAPP_TOKEN` de produção (agora
  também no backend); o `sub` da pessoa que respondeu; o JWT do Access; o e-mail da pessoa (dentro do
  JWT, usado só para derivar o primeiro nome mostrado ao turista, sem ser guardado nem logado).
- **Fronteiras de confiança:** navegador → painel → proxy → backend (JWT, ADR-0006); backend → Cloud
  API da Meta (token); n8n → backend (`INGEST_API_TOKEN`). O texto digitado pelo atendente e o do
  turista são dados não confiáveis.

## Diagrama de fluxo (texto)

```
atendente --(sessão do Access)--> painel --POST /api/conversations/{id}/mensagens (X-Panel-Request, client_message_id)-->
  proxy --JWT--> backend: confere login, estado = humano, janela de 24 h, teto por hora, texto
        --> Cloud API da Meta (para o telefone DA CONVERSA) --> turista
        --> (só se a Meta aceitou) grava a mensagem: autor = atendente, autor_sub, client_message_id

turista --> Meta --> n8n --POST /api/ingest/conversas/atendimento {telefone} (INGEST_API_TOKEN)--> backend
  estado = humano  --> n8n só registra a mensagem do turista (ingest só de entrada) e NÃO responde
  estado = ia      --> fluxo normal (catálogo, Gemini, resposta, registro)
  consulta falhou  --> contingência
```

## Ameaças (STRIDE)

Testes de backend em `backend/tests/test_human_handoff.py` e `test_human_handoff_security.py`; do
painel em `frontend/tests/unit/` (Vitest). Todos são escritos antes do código (TDD).

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | Enviar mensagem como a agência sem estar logado, ou com o token do n8n | WhatsApp falso em nome da agência | A rota usa a mesma autenticação do painel (JWT do Access, CSRF); o `INGEST_API_TOKEN` não abre a rota de envio, e o JWT do painel não abre o ingest | `test_send_requires_a_valid_panel_login`, `test_ingest_token_cannot_take_over_or_send`, `test_ingest_conversation_state_rejects_the_panel_jwt` | Baixo |
| **S**poofing | Mandar a mensagem para outro número (destinatário vindo do corpo ou de um id trocado) | Spam ou golpe a partir do número da agência | O destinatário é **sempre** o telefone da conversa informada na URL; o corpo não tem campo de telefone e campo extra é 422 (`extra="forbid"`); conversa inexistente é 404 | `test_send_goes_only_to_the_phone_of_the_conversation`, `test_handoff_routes_reject_bodies_with_forbidden_or_invalid_fields`, `test_send_to_an_unknown_conversation_is_404` | Baixo |
| **T**ampering | Enviar sem ter assumido, ou em conversa resolvida | IA e humano respondem ao mesmo tempo, ou resposta a quem já foi atendido | Só envia se `atendimento = humano` e a conversa não estiver resolvida; senão 409 | `test_send_requires_the_conversation_to_be_in_human_mode`, `test_send_to_a_conversation_the_attendant_no_longer_holds_is_refused` | Baixo |
| **T**ampering | Texto inválido ou gigante, caractere NUL, mensagem vazia | Erro da Meta, erro de banco, custo | Contrato estrito: 1 a 4096 caracteres, sem NUL, sem campos extras | `test_handoff_routes_reject_bodies_with_forbidden_or_invalid_fields` | Nenhum |
| **T**ampering | Clique duplo ou nova tentativa manda a mensagem duas vezes ao turista | Mensagem duplicada | `client_message_id` único: repetir devolve o resultado da primeira vez e não envia de novo | `test_send_is_idempotent_by_client_message_id`, `test_send_concurrent_same_client_message_id_sends_once` | Baixo |
| **T**ampering | Duas pessoas (ou dois cliques) assumem a mesma conversa ao mesmo tempo | Dois avisos e dois nomes para o mesmo turista | A linha da conversa é travada (`FOR UPDATE`) e o estado é reavaliado depois da trava; o segundo pedido vira "mesma pessoa" (sem reenviar) ou 409 | `test_locked_conversation_query_asks_postgres_for_a_row_lock` (e a verificação manual em Postgres descrita no PR) | Baixo |
| **I**nformation disclosure | Telefone do turista na URL da consulta do n8n, que vai para o log de acesso do servidor | Telefone em log | A consulta é um POST com o telefone no corpo; GET com telefone na URL não existe (405) | `test_ingest_conversation_state_does_not_take_the_phone_in_the_url` | Baixo |
| **T**ampering | Texto com HTML ou script exibido no painel (XSS armazenado) | Script no navegador da equipe | O backend grava o texto como veio; o painel exibe como texto (React, sem `dangerouslySetInnerHTML`) | `test_send_stores_markup_verbatim`; `MessageBubble shows markup in a message as plain text` (já existe) | Baixo |
| **S**poofing | Fazer-se passar por outra pessoa no aviso de "agora é um humano falando" | O turista é enganado sobre quem fala | O nome vem **só** do claim do JWT verificado (assinatura, emissor, audiência), nunca do corpo nem de cabeçalho; o corpo de "assumir" não tem campo de nome | `test_take_over_name_comes_only_from_the_verified_jwt`, `test_handoff_routes_reject_bodies_with_forbidden_or_invalid_fields` | Baixo |
| **T**ampering | Nome estranho ou malicioso (e-mail com símbolos, quebra de linha, instrução) chega ao turista pelo aviso | Mensagem ofensiva ou enganosa enviada em nome da agência | O aviso é um **modelo fixo** por idioma; o nome é sanitizado: só letras (Unicode), até 30 caracteres, primeiro nome; sem nome válido o aviso sai sem nome | `test_announcement_uses_only_letters_of_the_first_name`, `test_announcement_without_a_usable_name_says_a_person_of_the_team`, `test_announcement_follows_the_language_of_the_conversation` | Baixo |
| **T**ampering | Assumir uma conversa que já está com outra pessoa, ou assumir duas vezes e mandar o aviso duas vezes | Dois atendentes, ou aviso duplicado | Assumir de novo pela mesma pessoa não reenvia; por outra pessoa é 409 com o nome de quem atende | `test_take_over_again_by_the_same_person_does_not_resend_the_announcement`, `test_take_over_a_conversation_held_by_another_person_is_409` | Baixo |
| **T**ampering | A Meta recusa o aviso (janela de 24 h fechada, erro) e a conversa mudaria para humano sem o turista saber | IA calada e turista sem aviso | O aviso é enviado **antes** de mudar o estado; se a Meta recusar, a conversa continua com a IA e nada é gravado | `test_take_over_with_the_window_closed_is_409_and_keeps_ia`, `test_take_over_meta_failure_keeps_ia_and_saves_nothing` | Baixo |
| **I**nformation disclosure | O e-mail da pessoa vai ao turista, ao log ou ao banco | Dado pessoal de funcionário exposto | Só o primeiro nome derivado é enviado e gravado (`humano_nome`); o e-mail não é gravado nem logado | `test_take_over_never_stores_logs_or_sends_the_email` | Baixo |
| **R**epudiation | Não saber quem respondeu ao turista | Disputa, sem prova | `messages.autor_sub` guarda a pessoa que enviou, e o log traz o `sub` e o resultado (sem texto nem telefone); `humano_sub` e `humano_desde` registram quem assumiu | `test_send_goes_to_the_phone_of_the_conversation_and_records_the_author`, `test_take_over_records_who_and_when`, `test_send_never_logs_text_phone_or_token` | Médio: sem tabela de auditoria append-only (TD-A5) |
| **I**nformation disclosure | Texto, telefone ou token da Meta em log, resposta de erro ou exceção | Vazamento de dado pessoal e de credencial | Log só com método, molde da rota, `sub` e resultado; a falha da Meta vira mensagem fixa ("não foi possível enviar") com o código de erro, sem corpo da resposta, URL ou token; erros do `httpx` não sobem com a URL (que leva o `phone_number_id`) | `test_send_never_logs_text_phone_or_token`, `test_send_meta_failure_does_not_echo_the_provider_error`, `test_send_meta_failure_saves_nothing_and_allows_the_same_retry` | Baixo |
| **I**nformation disclosure | O token da Meta de produção existe também no GitHub e no Cloud Run | Se vazar, envio de mensagens como a agência | Token do usuário do sistema com escopo só de mensagens, só em secret (nunca no repositório, no log ou na conversa), com rotação documentada; a rota de envio só funciona com login | n/a (operacional) | **Médio:** segundo lugar para a credencial (o ADR descreve a alternativa de enviar pelo n8n) |
| **D**enial of service | Atendente (ou login comprometido) envia mensagens em massa | Custo, bloqueio do número pela Meta | Teto de 60 mensagens de atendente por conversa por hora (429); texto limitado; só conversas existentes | `test_send_is_capped_per_conversation_per_hour` | **Médio:** sem limite geral por todas as conversas (TD-A3) |
| **D**enial of service | IA muda para silêncio para sempre porque alguém esqueceu a conversa em `humano` | Turista sem resposta | Devolução automática para a IA depois de `HUMAN_HANDOFF_IDLE_HOURS` (padrão 2) sem mensagem do atendente | `test_state_returns_to_ia_after_the_idle_hours` (parametrizado nos dois lados do corte) | Baixo |
| **D**enial of service | A consulta do estado fica fora do ar | O n8n responderia por cima de um humano, ou trava | A consulta falha → o n8n cai na contingência (não responde com a IA no escuro); timeout curto e 3 tentativas | Fluxo do n8n exportado: nó com `onError` para a contingência (conferido por leitura e no teste ponta a ponta) | Baixo |
| **E**levation of privilege | Quem tem o token do n8n assume conversas ou envia mensagens | Escrita além do necessário | O `INGEST_API_TOKEN` só lê o estado e grava entradas; assumir, devolver e enviar exigem o login do painel | `test_ingest_token_cannot_take_over_or_send`, `test_ingest_conversation_state_does_not_take_the_phone_in_the_url` | Baixo |
| **E**levation of privilege | Pessoa autorizada assume conversa de outra, ou todas | Qualquer pessoa da equipe fala por qualquer conversa | Aceito: sem papéis (como no ADR-0006); o registro de quem assumiu e respondeu dá a rastreabilidade | n/a | Médio: aceito |

## Decisões

Tomadas pelo Patrick em 2026-10-01 (aprovação do ADR-0008, com as opções recomendadas):

1. **Quem envia:** o backend direto pela Cloud API (o token de produção da Meta passa a existir também
   no GitHub e no Cloud Run).
2. **Nome no aviso ao assumir:** só o primeiro nome, derivado do login.
3. **Aviso ao devolver para a IA:** uma mensagem curta ao turista.
4. **Devolução automática:** 2 horas sem mensagem do atendente.
5. **Teto de envio:** 60 mensagens de atendente por conversa por hora.
6. **Migração:** esta entrega usa a `0004`; a do agendamento (Leandro) passa a `0005`.

Pendente (bloqueia só o teste real, não o desenvolvimento): o Patrick coloca o `WHATSAPP_TOKEN` e o
`WHATSAPP_PHONE_NUMBER_ID` do número de produção nos secrets do GitHub.

## Riscos aceitos

- Qualquer pessoa autorizada assume qualquer conversa (sem papéis). **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0008).**
- O token de produção da Meta passa a existir também no GitHub e no Cloud Run. **Aceite do
  Patrick: pendente.**
- Sem aviso em tempo real: o atendente depende da atualização da tela (15 s). **Aceite do Patrick:
  pendente.**
- Sem limite de taxa geral (TD-A3). **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0008).**
