# Threat model: passeio sugerido pela IA

- **Data:** 2026-09-30
- **Escopo:** o LLM (Groq) passa a devolver o `id` do passeio que recomendou; o backend valida esse
  `id`, guarda em `conversations.passeio_sugerido_id` e o painel mostra o card "Passeio sugerido pela
  IA". Fica de fora: o cadastro de passeios (já coberto pelo CRUD) e o envio da resposta ao WhatsApp.
- **Dados sensíveis:** texto da mensagem do turista (vai ao Groq e fica na conversa), telefone (nunca
  vai ao Groq). O passeio sugerido é dado público do catálogo.
- **Fronteiras de confiança:** turista (WhatsApp) → webhook; backend → Groq (terceiro, não confiável);
  backend → banco; painel → API (autenticada).

## Diagrama de fluxo (texto)

```
turista --texto--> webhook (HMAC) --texto delimitado e limitado--> Groq
Groq --JSON {resposta, passeio_sugerido_id}--> backend
backend --id validado contra os passeios candidatos--> banco (conversations.passeio_sugerido_id)
painel --Bearer--> GET /api/conversations/{id} --> card (texto, nunca HTML)
```

## Ameaças (STRIDE)

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | Webhook forjado para induzir sugestões | Sugestão falsa no painel | HMAC em tempo constante (já existente) | `test_security.py::test_webhook_rejects_invalid_signature` | Nenhum novo |
| **T**ampering | Injeção de prompt faz o modelo devolver um `id` arbitrário ou inexistente | Card com passeio que o bot nunca viu | O `id` só vale se estiver entre os passeios candidatos enviados ao modelo; qualquer outro é descartado | `test_suggested_tour.py::test_suggested_tour_outside_the_candidates_is_discarded`, `test_security.py::test_prompt_injection_cannot_plant_a_tour_suggestion` | O modelo pode escolher um candidato ruim (erro de qualidade, não de segurança) |
| **T**ampering | Texto do turista fecha o delimitador `</mensagem_do_turista>` e escreve instruções | Texto vira instrução | Todo `<` e `>` (e os parecidos: `＜ ＞ ‹ › ⟨ ⟩`) é removido do texto do turista antes de montar a mensagem; nenhuma emenda de pedaços reconstrói a marca | `test_groq_client.py::test_user_text_cannot_close_the_delimiter`, `test_user_text_loses_lookalikes_of_the_angle_brackets` | Modelos podem ainda seguir instruções escondidas no texto; a saída é validada de qualquer forma |
| **T**ampering | `id` malicioso (SQL, HTML, texto enorme) devolvido pelo modelo | Injeção | Só aceita `str` com até 64 caracteres; depois só o que está na lista permitida; acesso ao banco só por ORM | `test_groq_client.py::test_parse_reply_rejects_unusable_suggested_ids`, `test_suggested_tour.py::test_suggested_tour_outside_the_candidates_is_discarded` | Nenhum |
| **T**ampering | Saída do modelo com tipo ou tamanho inesperado (idioma em lista, resposta gigante ou não-JSON) derruba o webhook ou estoura o limite do WhatsApp | 500 e turista sem resposta | `parse_reply` valida cada campo: idioma só `pt/en/es`, resposta `str` de até 4000 caracteres (também no caminho de JSON inválido), id `str` de até 64 | `test_groq_client.py::test_parse_reply_falls_back_to_portuguese_for_unknown_languages`, `test_parse_reply_caps_the_reply_length_and_requires_text`, `test_parse_reply_caps_the_length_of_a_reply_that_is_not_json` | Resposta ausente ou nula ainda devolve o JSON bruto ao turista (comportamento anterior) |
| **R**epudiation | Não saber qual sugestão foi dada | Disputa sobre a recomendação | A conversa guarda as mensagens e a sugestão fica na conversa; sem dado sensível novo | `test_suggested_tour.py::test_suggested_tour_is_saved_on_the_conversation` | Não guarda histórico de sugestões anteriores (só a última); aceito |
| **I**nformation disclosure | Telefone ou prompt de sistema vazam para o Groq ou para o cliente | Dado pessoal em terceiro | A mensagem ao Groq só leva o texto do turista e o catálogo; o telefone não é enviado; o painel só recebe dados públicos do passeio | `test_suggested_tour.py::test_groq_receives_no_phone_number` | O texto do turista pode conter dado pessoal que ele mesmo digitou; já era assim. O log de contingência do Groq leva só a classe da exceção e o status HTTP (nunca o texto do erro, que poderia ter URL ou chave), provado por `test_suggested_tour.py::test_groq_outage_logs_the_cause_without_personal_data` |
| **D**enial of service | Mensagem gigante gera custo e travamento no Groq | Custo e lentidão | Texto limitado a 1000 caracteres antes da chamada; `id` limitado a 64 | `test_groq_client.py::test_user_message_is_truncated_before_reaching_groq` | Sem limite de taxa por telefone (dívida TD-A3) |
| **D**enial of service | Groq indisponível (queda, timeout, 429/5xx, corpo fora do formato) | Webhook devolvia 500 e o turista ficava sem resposta | `ask_groq` converte qualquer falha em `GroqUnavailableError`; o tratador responde com mensagem de contingência trilíngue, grava a troca, marca a conversa como "precisa de atenção" (atendimento humano) e devolve 200 | `test_groq_client.py::test_ask_groq_raises_a_domain_error_when_the_provider_fails`, `test_suggested_tour.py::test_groq_outage_sends_a_fallback_and_asks_for_a_human`, `test_suggested_tour.py::test_webhook_answers_200_when_groq_is_down` | O turista recebe a mensagem de contingência, não a recomendação; a equipe é avisada pelo status |
| **E**levation of privilege | Saída do modelo dispara ação (marcar resolvida, enviar algo) | Ação sem autorização | Só dois campos tipados da saída têm efeito: o booleano de atenção humana (já existente) e o `id` validado; qualquer outro campo (ex.: `status`) é ignorado e nenhuma ação nasce de texto livre | `test_suggested_tour.py::test_unexpected_model_fields_change_nothing` | O modelo ainda decide o booleano de atenção humana (existente, efeito limitado a `aberta`/`precisa_atencao`) |

## Riscos aceitos

- Apenas a última sugestão fica guardada por conversa: o card mostra a mais recente e o histórico
  completo está nas mensagens. **Proposto; aguarda o aceite do Patrick.**
