# Threat model: fotos dos passeios (upload no painel e envio pela IA e pelo atendente)

- **Data:** 2026-10-01
- **Escopo:** subir, guardar, listar e apagar fotos de passeio pelo painel; enviar fotos ao turista
  pelo WhatsApp, pela IA (via n8n) e pelo atendente (ADR-0009). Fora de escopo: foto enviada **pelo
  turista**, vídeo e catálogo de produto da Meta.
- **Dados sensíveis:** as fotos (podem ter pessoas, EXIF e GPS); o telefone do turista; o
  `WHATSAPP_TOKEN` (já no backend pelo ADR-0008); o `sub` de quem subiu e de quem enviou.
- **Fronteiras de confiança:** navegador → painel → backend (arquivo enviado é **não confiável**);
  backend → bucket privado do Cloud Storage (pela conta de serviço do Cloud Run, sem chave);
  backend → Cloud API da Meta (upload de mídia e envio); n8n → backend (`INGEST_API_TOKEN`); a saída
  do LLM (`mostrar_fotos_passeio_id`) é dado de terceiros.

## Diagrama de fluxo (texto)

```
equipe --(login)--> painel --POST /api/tours/{id}/fotos (multipart, X-Panel-Request)--> backend
  valida: tipo pelo conteúdo, tamanho, nº de fotos, pixels --> reencoda JPEG (sem EXIF)
  --> bucket privado do Cloud Storage (só cria, nunca sobrescreve) --> linha de metadados no Neon

IA: Gemini --mostrar_fotos_passeio_id (id do catálogo com fotos)--> n8n --POST /api/ingest/conversas/fotos
      (INGEST_API_TOKEN, telefone, passeio_id)--> backend
Atendente: painel --POST /api/conversations/{id}/fotos (login, X-Panel-Request, foto_ids)--> backend
backend (comum): estado ≠ humano (se for a IA), janela de 24 h, tetos, destinatário = telefone da conversa
  --> lê o objeto do bucket --> sobe a foto à Meta (media_id em cache) --> envia a imagem
  --> (se a Meta aceitou) grava a mensagem
```

## Ameaças (STRIDE)

Testes de backend em `backend/tests/test_tour_photos.py` e `test_tour_photos_security.py`; do painel
em `frontend/tests/unit/`. Todos são escritos antes do código (TDD).

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | Subir, apagar ou enviar foto sem estar logado, ou com o token do n8n nas rotas do painel | Catálogo adulterado, fotos enviadas em nome da agência | As rotas do painel usam o login do ADR-0006 com CSRF; o `INGEST_API_TOKEN` só abre a rota de pedido da IA; o JWT do painel não abre o ingest | `test_photo_upload_requires_a_panel_login`, `test_photo_routes_reject_the_ingest_token`, `test_ingest_photo_request_rejects_the_panel_jwt` | Baixo |
| **T**ampering | Arquivo disfarçado (script ou executável com extensão `.jpg`, polyglot), ou SVG com script | Execução ou XSS ao exibir | O tipo vem do **conteúdo** decodificado; só JPEG, PNG e WebP; tudo é reencodado como JPEG (o arquivo original nunca é servido); SVG e outros tipos são 415 | `test_upload_rejects_a_script_renamed_as_jpg`, `test_upload_rejects_svg`, `test_upload_serves_only_the_reencoded_jpeg`, `test_upload_rejects_unsupported_formats[gif|svg|pdf|exe]` | Baixo |
| **T**ampering | "Bomba de descompressão" ou imagem gigante, ou muitas fotos de uma vez | Esgota memória e o banco | Limite de pixels do Pillow e de tamanho do arquivo (5 MB), no máximo 5 fotos por passeio e 60 no total; corpo lido com teto | `test_upload_rejects_a_decompression_bomb`, `test_upload_rejects_a_file_over_5_mb`, `test_upload_rejects_the_sixth_photo_of_a_tour`, `test_upload_rejects_when_the_global_cap_is_reached` | Baixo |
| **T**ampering | Foto trocada de passeio ou apagada de outro por id forjado | Foto errada no catálogo | O id da foto pertence a um passeio na URL; foto de outro passeio é 404; passeio inexistente é 404 | `test_photo_of_another_tour_is_404`, `test_photo_delete_of_an_unknown_tour_is_404` | Baixo |
| **T**ampering | Mandar a foto para outro número (destinatário vindo do corpo) | Spam em nome da agência | O destinatário é **sempre** o telefone da conversa; o corpo não tem campo de telefone (campo extra é 422) | `test_send_photos_goes_only_to_the_phone_of_the_conversation`, `test_send_photos_rejects_a_body_with_a_phone_field` | Baixo |
| **T**ampering | Prompt injection faz a IA pedir foto de um passeio que não existe, sem foto, ou de outro tema | Foto indevida ao turista | `mostrar_fotos_passeio_id` só vale se o passeio existir, estiver ativo **e tiver foto** (lista de permitidos); senão o pedido é ignorado e logado sem o valor | `test_ai_photo_request_for_an_unknown_tour_is_ignored`, `test_ai_photo_request_for_a_tour_without_photos_is_ignored`, `test_ai_photo_request_for_an_inactive_tour_is_ignored` | Médio: sem guardrail dedicado contra injeção (aceito no ADR-0004) |
| **T**ampering | A IA envia foto com a conversa em modo humano, ou fora da janela de 24 h | A IA fala por cima de uma pessoa, ou erro da Meta | A rota de pedido da IA confere o estado (`ia`) e a janela de 24 h; senão 409 | `test_ai_photo_request_is_refused_in_human_mode`, `test_photo_send_outside_the_24h_window_is_409` | Baixo |
| **R**epudiation | Não saber quem subiu, apagou ou enviou uma foto | Disputa, sem prova | `tour_photos` guarda `criada_por_sub`; a mensagem de imagem guarda o autor (`ia` ou `atendente`) e `autor_sub`; o log traz o `sub` e o resultado, sem bytes nem telefone | `test_upload_records_who_uploaded`, `test_photo_message_records_the_author`, `test_photo_actions_log_the_actor_without_phone` | Médio: sem auditoria append-only (TD-A5) |
| **I**nformation disclosure | EXIF ou GPS da foto (modelo do aparelho, local) vai ao turista ou fica no banco | Dado pessoal de quem fotografou | A foto é reencodada sem metadados antes de ser guardada | `test_upload_strips_exif_and_gps` | Baixo |
| **I**nformation disclosure | Foto com pessoas reconhecíveis sem autorização | LGPD e direito de imagem | Aviso no formulário; responsabilidade de quem sobe; a demonstração pública usa ilustrações, não fotos reais | Manual (revisão do formulário no QA) | **Médio:** não há como o sistema reconhecer rostos; depende da equipe |
| **I**nformation disclosure | Endereço público da foto adivinhado ou indexado | Foto acessível sem login | Não há endereço público: o painel serve as fotos só autenticado, e o envio usa o `media_id` da Meta | `test_photo_download_requires_a_panel_login` | Baixo |
| **I**nformation disclosure | Erro da Meta, bytes da foto, telefone ou token em log, resposta ou exceção | Vazamento | Log só com `sub`, molde da rota e resultado; erro da Meta vira mensagem fixa; `httpx` não sobe a URL | `test_photo_send_never_logs_bytes_phone_or_token`, `test_photo_send_meta_failure_does_not_echo_the_provider_error`, `test_photo_send_meta_failure_does_not_save_the_message` | Baixo |
| **D**enial of service | A IA (ou um login comprometido) manda fotos em excesso | Custo, bloqueio do número pela Meta | No máximo 3 fotos por pedido e 10 por conversa por hora, somando IA e atendente (429) | `test_photo_send_is_capped_per_request`, `test_photo_send_is_capped_per_conversation_per_hour` | **Médio:** sem limite geral (TD-A3) |
| **D**enial of service | Enviar a mesma foto várias vezes por repetição de pedido | Foto duplicada ao turista | O pedido leva um `client_request_id` único: repetir não reenvia | `test_photo_send_is_idempotent_by_client_request_id` | Baixo |
| **D**enial of service | `media_id` expirado ou recusado pela Meta | Foto não sai | O envio sobe a foto de novo quando a validade passou ou a Meta recusa o id, uma vez; se falhar, 502 sem gravar | `test_photo_send_reuploads_when_the_media_id_expired`, `test_photo_send_retries_the_upload_once_then_fails` | Baixo |
| **I**nformation disclosure | Bucket exposto ao público por configuração errada (acesso público, `allUsers`) | Todas as fotos acessíveis na Internet | Prevenção de acesso público **ativa** e acesso uniforme em nível de bucket (configuração conferida pela API, só leitura, antes de subir a primeira foto e a cada mudança de permissão); o código nunca gera endereço público nem assinado; o painel serve as fotos pelo backend autenticado | `test_photo_download_requires_a_panel_login`; conferência por API documentada em `docs/deploy.md` | Médio: a proteção do bucket é configuração fora do código (do Patrick) |
| **E**levation of privilege | A conta de serviço do Cloud Run com permissão larga demais no Cloud Storage | Um vazamento do backend leria ou apagaria todos os buckets do projeto | O papel `roles/storage.objectUser` é dado **só neste bucket** (nunca no projeto); sem chave JSON (a organização bloqueia) | n/a (configuração conferida pela API, só leitura) | Baixo |
| **T**ampering | Objeto órfão (falha entre o bucket e o banco) ou linha sem objeto | Foto sumida no painel ou lixo no bucket | Ordem fixa: sobe o objeto e depois grava a linha; ao apagar, tira a linha e depois o objeto; linha sem objeto vira erro tratado (404 no painel, pedido ignorado na IA), e o comando de limpeza remove órfãos | `test_upload_failure_after_the_object_leaves_no_row`, `test_delete_removes_the_row_before_the_object`, `test_photo_row_without_object_is_handled`, `test_purge_orphan_photos_removes_only_objects_without_a_row` | Baixo |
| **T**ampering | O envio sobrescreve ou troca um objeto existente | Foto trocada sem rastro | O upload usa a condição "só cria" (`if_generation_match=0`); a chave do objeto traz o `sha256` | `test_upload_never_overwrites_an_existing_object` | Baixo |
| **D**enial of service | O bucket (ou a permissão) fica indisponível | Foto não sobe, não aparece ou não sai | Painel mostra erro claro; a IA segue só com o texto (nunca falha a resposta ao turista); 502 sem gravar mensagem | `test_storage_failure_on_upload_is_502_and_saves_nothing`, `test_ai_photo_request_when_storage_is_down_keeps_the_text_reply` | Baixo |
| **I**nformation disclosure | Fotos guardadas nos EUA (região do plano gratuito) quando tiverem pessoas | Transferência internacional de dado pessoal (LGPD) | Região `us-central1` só para fotos de passeio **sem** pessoas; com pessoas, o bucket vai para `southamerica-east1` (Brasil), com a decisão de custo do Patrick | Manual (revisão do formulário e da região do bucket no QA) | **Médio:** depende de quem sobe a foto |
| **E**levation of privilege | Quem tem o token do n8n sobe, apaga ou lista fotos | Escrita além do necessário | O `INGEST_API_TOKEN` só pede o envio das fotos de um passeio e lê a quantidade no catálogo; subir e apagar exigem login | `test_ingest_token_cannot_upload_or_delete_photos` | Baixo |

## Decisões

Tomadas pelo Patrick em 2026-10-01 (aprovação do ADR-0009, com as opções recomendadas):

1. **Onde guardar:** bucket privado do Cloud Storage.
2. **Região:** `us-central1` (plano gratuito), só para fotos de passeio **sem pessoas reconhecíveis**.
3. **Quem sobe:** a equipe, pelo painel.
4. **Origem das fotos:** da própria agência ou de banco de imagens de licença livre, sem pessoas.
5. **Tetos:** 5 fotos por passeio, 60 no total, 3 por pedido e 10 por conversa por hora.
6. **Ordem:** depois do atendimento humano (ADR-0008), que traz o envio pela Cloud API.

Pendente (do Patrick, antes de subir a primeira foto): criar o bucket privado com prevenção de acesso
público e dar `roles/storage.objectUser` à conta de serviço do Cloud Run só nele.

## Riscos aceitos

- Foto com pessoas e direitos de imagem dependem de quem sobe. **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0009).**
- Sem guardrail dedicado contra prompt injection na saída do modelo (já aceito no ADR-0004).
  **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0009).**
- Sem limite de taxa geral (TD-A3). **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0009).**
- Mais uma dependência com histórico de CVEs de decodificação (Pillow) e o cliente do Cloud
  Storage. **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0009).**
- Fotos sem pessoas guardadas numa região dos EUA (plano gratuito). **Aceito pelo Patrick em 2026-10-01 (aprovação do ADR-0009).**
