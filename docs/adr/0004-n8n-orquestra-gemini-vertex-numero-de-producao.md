# ADR-0004: Orquestrar o atendimento no n8n, usar Gemini no Vertex AI e um número +55 de produção

- **Status:** Proposto
- **Data:** 2026-10-01
- **Autores:** Patrick (decisão e requisitos); redação por Claude Code
- **Checklist afetado:** GOV-1, AI-1, AI-2, AI-3, SEC-1, SEC-7, OBS-3, DATA-1, INF-4

## Contexto

Fatos, em 2026-10-01:

- O fluxo original recebe o webhook da Meta no backend FastAPI (HMAC, deduplicação por id da
  mensagem, transcrição com faster-whisper, resposta do Groq `openai/gpt-oss-120b`, gravação no
  banco para o painel). `docs/decisoes-de-arquitetura.md` fixou **custo zero** e descartou o
  Gemini porque a API de desenvolvedor exigia crédito pré-pago.
- O app da Meta usava o **número de teste dos EUA** numa conta WhatsApp de teste. Mensagens para
  o Brasil entravam e eram respondidas pela API, mas a entrega falhava com o erro **130497**
  (*Business account is restricted from messaging users in this country*), medido em três
  execuções. Registrar um **número brasileiro (+55) de produção** numa conta nova (moeda BRL)
  eliminou o erro: o status passou a `sent` e `delivered`, sem cobrança (`free_customer_service`).
- A organização Google Cloud bloqueia chave JSON de service account
  (`iam.managed.disableServiceAccountKeyCreation`). O projeto GCP já tinha billing ativo e
  rodava o backend no Cloud Run.
- O n8n Cloud da Rovan está disponível e o Patrick pediu para orquestrar os fluxos nele e usar a
  IA do Google Cloud.
- Um fluxo equivalente foi construído e testado: `docs/n8n/`.

## Opções avaliadas

1. **Manter backend + Groq.** Custo zero e nada a mudar. Não atende ao pedido de usar n8n e
   Google Cloud. A troca para o número +55 resolve a entrega **independentemente** desta decisão.
2. **Só trocar o LLM por Gemini dentro do backend** (Vertex AI, sem chave: o Cloud Run usa a
   identidade da service account). Mudança pequena, preserva HMAC com tempo constante,
   deduplicação, áudio, painel e testes. Custo: cobrança por token do Gemini; nada de n8n.
3. **n8n orquestra, backend vira API, Gemini no Vertex AI.** Prompt e fluxo editáveis sem deploy,
   mesma ferramenta para outras automações. Custo: plano do n8n, chave JSON de service account
   guardada no n8n, e reimplementar no n8n ou no backend o que o webhook do backend já fazia.
4. **Tudo no n8n, sem backend.** Descartada: perde banco, painel, testes e regras de LGPD.

## Decisão

Adotar a **opção 3**, em etapas, por escolha do Patrick: o n8n recebe o webhook da Meta, busca o
catálogo no backend, chama o **Gemini 2.5 Flash no Vertex AI** e responde pelo **número +55 de
produção**. O backend continua dono dos dados (catálogo, conversas, painel).

- **Etapa 1 (feita e em operação de teste):** WhatsApp → n8n → catálogo (`GET /api/tours`) →
  Gemini → resposta. Sem gravação no painel. Contingência trilíngue se o modelo ou o catálogo
  falharem.
- **Etapa 2 (pendente, exige ADR/threat model próprios):** endpoint de entrada no backend para o
  n8n registrar conversas e mensagens, deduplicação por id, transcrição de áudio e filtro de
  candidatos do catálogo (`tour_matcher`).

## Consequências positivas

- Prompt, modelo e fluxo mudam sem build nem deploy do backend.
- Latência medida: catálogo 1,8 s (5,6 s com Cloud Run frio), Gemini 0,9 a 1,5 s, envio ~1 s.
- Respostas validadas por esquema JSON; idioma restrito a `pt|en|es`.
- Sem dependência do Groq no fluxo de produção.
- Responder dentro de 24 h do contato do turista não gera cobrança da Meta (observado nos avisos
  de status: `billable: false`).

## Riscos e trade-offs

- **O custo deixa de ser zero.** Estimativa: Gemini ≈ US$ 0,00075 por mensagem (≈ 1.500 tokens de
  entrada e ≈ 100 de saída, estimados pelo n8n; preço de US$ 0,30 / US$ 2,50 por milhão de tokens,
  a confirmar na página oficial) e plano do n8n Cloud (Starter ≈ €20 a 24/mês, 2.500 execuções).
  Cada mensagem gera ≈ 5 execuções no n8n porque os avisos de status da Meta também disparam o
  gatilho. Mitigação proposta: assinar só o status `failed` (≈ 1 execução por mensagem).
  **Este ADR exige revisar `INF-4` e `AI-3` do checklist e a regra "custo zero é requisito" do
  `CLAUDE.md`; essas edições são do Patrick, não foram feitas aqui.**
- **Chave JSON de service account no n8n.** A política da organização foi relaxada no projeto para
  criá-la. Mitigação: reativar a política, papel único `roles/aiplatform.user`, rotacionar a chave
  e guardá-la só na credencial do n8n. A opção 2 evitaria esse risco por completo.
- **Dados pessoais no n8n Cloud.** Telefone e texto do turista ficam nas execuções. Exige política
  de retenção (LGPD); ver o threat model.
- **O painel não mostra as conversas do n8n até a etapa 2.** Enquanto isso o "precisa de
  atendimento humano" só existe no texto da resposta.
- **Duas fontes do prompt** (backend e n8n) até a etapa 2.
- **Webhook sem deduplicação e comparação de HMAC não constante** no gatilho do n8n.
- **Token do usuário do sistema da Meta** sem expiração e com permissões padrão: precisa ser
  revisto para só `whatsapp_business_messaging`.
- A verificação da empresa na Meta está em análise (cerca de 2 dias úteis); ela eleva limites, mas
  não bloqueia o fluxo atual.

## Plano de adoção e reversão

1. Aprovação deste ADR pelo Patrick e atualização dos itens do checklist citados acima.
2. Reduzir execuções (status `failed` apenas) e configurar retenção de execuções no n8n.
3. Reativar a política de chaves de service account, rotacionar a chave do Vertex e revisar o
   token do usuário do sistema.
4. Etapa 2: ADR e threat model do endpoint de entrada; mover os testes de segurança (HMAC,
   deduplicação, injeção de prompt) para `backend/tests/`.
5. **Reversão:** desativar o workflow no n8n e apontar o callback do app Meta de volta para
   `https://<backend>/webhook/whatsapp` com o `WHATSAPP_VERIFY_TOKEN`. O código do Groq e do
   webhook continua no backend, intacto. É preciso atualizar `WHATSAPP_TOKEN` e
   `WHATSAPP_PHONE_NUMBER_ID` no Cloud Run para os da conta de produção.
