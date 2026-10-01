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
WhatsApp → Meta → [Receber WhatsApp] → [Só mensagens de texto] → [Buscar catálogo]
        → [Preparar entrada] → [Gerar resposta (Gemini 2.5 Flash, Vertex AI)] → [Enviar resposta]
                 falha no catálogo ou no modelo → [Enviar aviso de contingência]
```

- O gatilho valida a assinatura `X-Hub-Signature-256` com o App Secret e descarta o que não confere.
- O texto do turista é limpo (`<` `>` e equivalentes Unicode removidos, máximo de 1000 caracteres)
  e entra no prompt como **dado delimitado**. O telefone não vai ao modelo.
- A saída do Gemini é validada por esquema JSON (`idioma` ∈ `pt|en|es`, `passeio_sugerido_id`
  texto ou nulo). Resposta enviada tem no máximo 4000 caracteres.
- O catálogo vem de `GET /api/tours` e é tentado até 3 vezes (o Neon fecha conexões ociosas).
- O raciocínio do modelo está desligado (`thinkingBudget: 0`); ligado, ele consome o teto de
  tokens e a resposta vem vazia.

## Credenciais que o workflow usa (nomes no n8n)

Crie cada uma em **Credentials** e ligue ao nó correspondente depois de importar.

| Credencial | Tipo | Nó | O que guarda |
|---|---|---|---|
| WhatsApp OAuth account | WhatsApp OAuth API | Receber WhatsApp | ID do app Meta e App Secret |
| WhatsApp account | WhatsApp API | Enviar resposta, Enviar aviso | Token do usuário do sistema da Meta e ID da conta WhatsApp Business |
| Simplified Custom Auth account | Simplified Custom Auth | Buscar catálogo | Modelo `{"headers":{"Authorization":"Bearer {{api_key}}"}}` e o `DASHBOARD_API_TOKEN` |
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
