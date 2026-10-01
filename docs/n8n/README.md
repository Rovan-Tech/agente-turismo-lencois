# Fluxo do WhatsApp no n8n

Exportação versionada do workflow **Agente Turismo - WhatsApp (Gemini Vertex)**, descrito no
[ADR-0004](../adr/0004-n8n-orquestra-gemini-vertex-numero-de-producao.md) (Proposto) e analisado em
[`docs/threat-models/2026-10-01-n8n-gemini-whatsapp.md`](../threat-models/2026-10-01-n8n-gemini-whatsapp.md).

O arquivo `agente-turismo-whatsapp.workflow.json` **não tem credenciais, IDs de webhook nem IDs de
serviços de terceiros**. Dois marcadores precisam ser trocados depois de importar:

| Marcador | O que colocar |
|---|---|
| `<BACKEND_URL>` | URL do serviço `agente-turismo-lencois-backend` no Cloud Run |
| `<GCP_PROJECT_ID>` | Projeto do Google Cloud onde o Vertex AI está habilitado |

## Como funciona

```
WhatsApp → Meta → [Receber WhatsApp] → [Só mensagens de texto] → [Consultar atendimento]
        → [Uma pessoa está atendendo?] ─ sim → [Registrar mensagem (atendente ativo)]  (e não responde)
                                       └ não → [Buscar catálogo] → [Preparar entrada]
        → [Gerar resposta (Gemini 2.5 Flash, Vertex AI)] → [Enviar resposta]
                                                         → [Registrar atendimento no painel]
   falha na consulta, no catálogo ou no modelo → [Enviar aviso de contingência]
                                               → [Registrar atendimento (contingência)]
```

- O gatilho valida a assinatura `X-Hub-Signature-256` com o App Secret e descarta o que não confere.
- O texto do turista é limpo (`<` `>` e equivalentes Unicode removidos, máximo de 1000 caracteres)
  e entra no prompt como **dado delimitado**. O telefone não vai ao modelo.
- A saída do Gemini é validada por esquema JSON (`idioma` ∈ `pt|en|es`, `passeio_sugerido_id`
  texto ou nulo). Resposta enviada tem no máximo 4000 caracteres.
- **Atendimento humano (ADR-0008):** antes de tudo, "Consultar atendimento" pergunta ao backend
  (`POST /api/ingest/conversas/atendimento`, telefone no corpo, `INGEST_API_TOKEN`) quem responde
  àquele telefone. Com `humano` (uma pessoa assumiu a conversa no painel), o fluxo **só registra** a
  mensagem do turista (`POST /api/ingest/mensagens`) e **não chama o Gemini nem responde**. Com
  `ia`, segue o fluxo normal. Se a consulta falhar (3 tentativas, 5 s cada), cai na contingência: o
  fluxo nunca responde "no escuro" por cima de um humano. O backend devolve a conversa para a IA
  depois de 2 horas sem mensagem do atendente.
- O catálogo vem de `GET /api/ingest/catalogo`, com o `INGEST_API_TOKEN` (o mesmo do registro de
  atendimentos), e é tentado até 3 vezes (o Neon fecha conexões ociosas). O n8n **não** usa o token do
  painel: com o painel atrás do Cloudflare Access (ADR-0006) esse token deixa de valer.
- **Registro no painel (ADR-0005):** depois de responder, o nó "Registrar atendimento" chama
  `POST /api/ingest/atendimentos` com o id da mensagem da Meta, o telefone, o texto original do
  turista (até 4096), a resposta enviada, `idioma`, `passeio_sugerido_id` e
  `precisa_atencao_humana`. São 3 tentativas com 10 s de limite; repetir é seguro (o backend
  deduplica pelo id). Se falhar, **não** dispara a contingência (o turista já foi respondido) e o
  atendimento fica só na execução do n8n. O backend só aceita passeio ativo do catálogo.
- **"Precisa de atenção"** (decisão do Patrick): `precisa_atencao_humana` é `true` só quando o
  modelo não sabe responder ou está em dúvida, ou o turista pede uma pessoa, e na contingência. O
  backend só escala o status; a marca sai quando uma pessoa resolve a conversa no painel.
- O raciocínio do modelo está desligado (`thinkingBudget: 0`); ligado, ele consome o teto de
  tokens e a resposta vem vazia.

## Credenciais que o workflow usa (nomes no n8n)

Crie cada uma em **Credentials** e ligue ao nó correspondente depois de importar.

| Credencial | Tipo | Nó | O que guarda |
|---|---|---|---|
| WhatsApp OAuth account | WhatsApp OAuth API | Receber WhatsApp | ID do app Meta e App Secret |
| WhatsApp account | WhatsApp API | Enviar resposta, Enviar aviso | Token do usuário do sistema da Meta e ID da conta WhatsApp Business |
| Ingest API Token account | Simplified Custom Auth | Consultar atendimento, Registrar mensagem, Buscar catálogo e Registrar atendimento (5 nós) | Modelo `{"headers":{"Authorization":"Bearer {{api_key}}"}}` e o `INGEST_API_TOKEN` |
| Google Service Account account | Google Service Account API | Gemini 2.5 Flash | E-mail e chave privada de uma service account com **só** `roles/aiplatform.user` |

**Nenhum segredo vai para o repositório.** Gere o token do WhatsApp como usuário do sistema, com
a permissão `whatsapp_business_messaging`, e anote a data para rotacionar.

## Configuração na Meta

1. O número **+55** de produção precisa estar registrado na conta WhatsApp Business (status
   *Inscrito*). Mensagens entre países diferentes são bloqueadas (erro 130497).
2. Em *Etapa 2 → Registre seu número*, ligue **Assinar webhooks** da conta, senão as mensagens
   não chegam ao app.
3. O callback do app aponta para a URL do gatilho do n8n, que o n8n registra ao ativar o
   workflow. **Isso tira o tráfego do backend** (`/webhook/whatsapp`); ver a reversão no ADR.

## Operação

- Cada mensagem gera ≈ 5 execuções no n8n, pois os avisos de status da Meta (`sent`, `delivered`…)
  também disparam o gatilho. Reduzir assinando só `failed` está em TD-N8 (`docs/tech-debt.md`).
- Dados pessoais ficam nas execuções do n8n Cloud: defina a retenção (TD-N5).
- Para testar sem enviar mensagem real, use uma cópia do workflow com um gatilho Webhook e sem os
  nós de envio.
