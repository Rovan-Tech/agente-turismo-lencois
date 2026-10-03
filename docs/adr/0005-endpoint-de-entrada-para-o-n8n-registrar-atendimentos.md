# ADR-0005: Criar um endpoint de entrada no backend para o n8n registrar os atendimentos

- **Status:** Aprovado (Patrick, 2026-10-01)
- **Data:** 2026-10-01
- **Autores:** Patrick (pedido); redação por Claude Code
- **Checklist afetado:** GOV-1, GOV-2, SEC-1, SEC-3, SEC-6, DATA-1, DATA-3, OBS-3, TEST-1
- **Depende de:** [ADR-0004](0004-n8n-orquestra-gemini-vertex-numero-de-producao.md) (ainda
  `Proposto`). Este ADR é a **etapa 2a** dele; sem a aprovação do 0004 não há o que registrar.

## Contexto

Fatos, em 2026-10-01:

- Desde o ADR-0004 o callback da Meta aponta para o n8n. O último `POST /webhook/whatsapp` que o
  backend recebeu foi em 26/09 às 03:39 (logs do Cloud Run). O turista é atendido (execução 18 do
  n8n, 13:51, respondida em 3 s), mas **nenhuma conversa chega ao banco**: o painel mostra só a
  conversa de 26/09 e a agência não vê os atendimentos novos nem os que pedem humano (TD-N3, Alta).
- O backend já sabe registrar um atendimento: `message_handler.py` cria ou reabre a conversa,
  grava a mensagem do turista com `whatsapp_message_id` único (barra reenvio), grava a resposta,
  atualiza idioma, passeio sugerido (validado contra uma lista permitida) e status.
- A saída do Gemini no n8n já traz `idioma`, `resposta`, `passeio_sugerido_id` e
  `precisa_atencao_humana` (a aba "Precisam de atenção" do painel depende dele); o critério dele no
  prompt precisava ser ajustado à decisão do Patrick, abaixo.
- O token do painel (`DASHBOARD_API_TOKEN`) está **em texto no bundle público** do site
  (`VITE_API_TOKEN`, TD-A6). Ele só pode proteger leitura; uma rota de escrita protegida por ele
  seria aberta a qualquer pessoa que baixe o JavaScript do painel.
- O serviço do Cloud Run é `--allow-unauthenticated` (a Meta precisa alcançá-lo), então a
  autenticação de uma rota nova é responsabilidade da aplicação.
- O ADR-0004 junta na "etapa 2" quatro coisas: endpoint de entrada, deduplicação, transcrição de
  áudio e filtro de candidatos do catálogo. O ADR-0003 pede entregas menores.

## Opções avaliadas

1. **Um endpoint idempotente que registra o atendimento inteiro numa chamada** — o n8n envia a
   resposta ao turista e depois chama `POST /api/ingest/atendimentos` com a mensagem recebida, a
   resposta enviada e os metadados. O backend valida, deduplica por `whatsapp_message_id`, grava
   as duas mensagens na mesma transação e devolve `criado` ou `duplicado`. Reaproveita as funções
   do `message_handler.py`. Prós: uma chamada, atômica, repetir é seguro, o backend continua dono
   das regras. Contras: o n8n responde antes de registrar, então uma falha do backend depois do
   envio deixa um atendimento sem registro (mitigado por 3 tentativas). Custo extra: zero (uma
   requisição a mais no Cloud Run, dentro da cota gratuita; sem execução extra no n8n).
2. **Duas fases: reservar e completar** — o n8n chama o backend **antes** de responder (reserva o
   `message_id`, o que também resolveria a resposta duplicada de TD-N1) e depois de responder
   (completa). Prós: fecha TD-N1. Contras: cria o estado "reservado e nunca completado" (precisa de
   prazo e limpeza), dois endpoints, mais nós no fluxo. É o próximo passo natural, mas aumenta a
   entrega; fica para um ADR próprio se TD-N1 for priorizado.
3. **O n8n grava direto no Neon** (nó Postgres) — Prós: sem código no backend. Contras: a
   credencial do banco vai para o n8n Cloud com permissão de escrita ampla; a lista permitida de
   passeios, a deduplicação e as regras de LGPD seriam reimplementadas no fluxo, fora dos testes do
   repositório. Descartada.
4. **Devolver o webhook ao backend** (reversão do ADR-0004) — o painel volta a mostrar tudo e a
   transcrição de áudio volta, mas o atendimento deixa de usar n8n e Gemini, que foi a escolha do
   Patrick. Continua disponível como reversão; não é a recomendação.
5. **Não fazer nada** — o painel fica sem os atendimentos novos e sem o aviso de "precisa de
   atenção humana"; TD-N3 segue **Alta**.

## Decisão

Adotar a **opção 1**: `POST /api/ingest/atendimentos`, protegido por um **token próprio**
(`INGEST_API_TOKEN`), diferente do token do painel, e que grava o atendimento reaproveitando o
código do `message_handler.py`. Por escolha de escopo, a **etapa 2 é dividida**: este ADR cobre só
2a (registrar texto). Transcrição de áudio (2b) e filtro de candidatos do catálogo (2c) terão ADR
próprio cada uma.

Contrato proposto (nomes iguais aos da saída do Gemini no n8n, para o mapeamento ser 1 para 1):

```json
{
  "whatsapp_message_id": "wamid.…",          // obrigatório, 1 a 128 caracteres
  "telefone": "5511912171865",               // só dígitos, 8 a 15
  "texto": "…",                              // o que o turista escreveu, 1 a 4096
  "resposta": "…",                           // o que foi enviado, 1 a 4096
  "idioma": "pt",                            // "pt" | "en" | "es" | null
  "passeio_sugerido_id": "passeio-…",        // texto ou null
  "precisa_atencao_humana": false            // obrigatório
}
```

Resposta: `{"status": "criado" | "duplicado", "conversa_id": "…"}`. Nunca devolve telefone nem texto.

Regras:

- **Autenticação**: `Authorization: Bearer <INGEST_API_TOKEN>`, comparação em tempo constante,
  **fail-closed** (token não configurado = 401 sempre). O token do painel **não** vale aqui e o do
  ingest **não** vale nas rotas do painel. O token vai só no cabeçalho, nunca na URL.
- **Validação**: Pydantic estrito, `extra="forbid"`, limites de tamanho, `idioma` restrito,
  corpo máximo de 16 KiB. `whatsapp_message_id` é obrigatório (sem ele não há idempotência).
- **Idempotência**: o índice único de `messages.whatsapp_message_id` decide. Repetir a chamada
  (reenvio da Meta, nova tentativa do n8n) devolve `duplicado` com HTTP 200 e não grava nada. Duas
  chamadas simultâneas com o mesmo id gravam uma vez.
- **Passeio sugerido**: só vale se existir e estiver **ativo**; senão vira `null` e o atendimento
  é gravado mesmo assim (o histórico pesa mais que a dica).
- **Status** (decisão do Patrick, 2026-10-01): "precisa de atenção" vale **só quando o bot não
  tem resposta ou está em dúvida**; nesse caso um atendente responde pela plataforma. Então
  `precisa_atencao_humana` verdadeiro → `precisa_atencao`; falso → o status **não muda** (conversa
  nova nasce `aberta`). A marca só sai quando uma pessoa marca a conversa como resolvida no painel:
  a rota **só escala, nunca rebaixa**, e não consegue marcar `resolvida`, nem tocar em passeios ou
  reservas. O critério ("sem resposta ou em dúvida") vai no prompt do n8n, e a contingência (modelo
  ou catálogo fora do ar) também envia `true`. Isso difere do webhook antigo do backend
  (`_record_reply`), que volta para `aberta`; o código antigo não muda nesta entrega.
- **Retenção** (decisão do Patrick, 2026-10-01): **90 dias**, o mesmo valor de
  `phone_retention_days` das reservas. Conversa sem atividade há mais de 90 dias é apagada
  **com as mensagens** (o texto do turista também pode ter dado pessoal), por uma rotina de
  expurgo entregue junto com o endpoint. Consequência: o histórico do painel tem 90 dias.
- **Mudança do n8n** (editável sem deploy do backend, exportação em `docs/n8n/`): adicionar
  critério de `precisa_atencao_humana` no prompt (o campo já existe no esquema de saída do Gemini);
  o ramo de contingência envia `precisa_atencao_humana: true`; um nó HTTP chama o ingest depois de cada envio, com 3 tentativas e
  **sem** acionar a contingência se falhar (a resposta ao turista já foi enviada).
- **Registros (OBS-3)**: o log traz só o resultado (`criado` ou `duplicado`), sem
  telefone, texto, token nem `whatsapp_message_id`. O erro 422 desta rota **não devolve o campo
  `input`** (o handler padrão do FastAPI ecoaria o telefone e o texto para o n8n, onde ficam nas
  execuções, TD-N5).

## Consequências positivas

- O painel volta a mostrar os atendimentos feitos pelo n8n, com idioma, passeio sugerido e a aba
  "Precisam de atenção". Fecha TD-N3.
- Nenhuma tabela nova nem migração: usa `conversations` e `messages`.
- Reenvio e nova tentativa são seguros e testáveis no repositório (hoje o n8n não tem teste, TD-N6).
- O token do painel continua só de leitura; um vazamento dele não permite forjar conversas.
- Custo zero adicional.

## Riscos e trade-offs

- **Registro pode se perder.** Se o backend ficar fora do ar durante as 3 tentativas, o atendimento
  já respondido não é gravado. O conteúdo fica só nas execuções do n8n. Aceitável para uma demo de
  portfólio; vira problema se o painel passar a ser a fonte oficial do atendimento.
- **Resposta duplicada continua** (TD-N1): este endpoint não impede que o n8n responda duas vezes
  a um reenvio da Meta; só impede o registro duplicado. A opção 2 resolve e fica para depois.
- **Nova credencial em um serviço público.** `INGEST_API_TOKEN` é o único portão da rota. Precisa
  de segredo no GitHub e no Cloud Run, valor forte e aleatório, rotação documentada e credencial
  no n8n. Vazou, vira escrita aberta; o interruptor é desativar a variável (a rota passa a 401).
- **Sem limite de taxa** (TD-A3, Alta): o teto de tamanho limita o dano por chamada, não a
  quantidade. Só o n8n tem o token.
- **Histórico limitado a 90 dias.** Hoje o telefone fica em `conversations.whatsapp_phone` para
  sempre e só as reservas têm expurgo. Com a retenção decidida, conversas inativas há mais de 90
  dias somem do painel, com as mensagens. A rotina de expurgo faz parte desta entrega; não existe
  hoje para conversas.
- **"Atendente responde pela plataforma" não existe ainda.** O painel só lê conversas e marca como
  resolvida; não envia mensagem. Quem atende hoje responde fora do painel (por exemplo, no app do
  WhatsApp Business). Enviar resposta pelo painel seria outra funcionalidade, com ADR e threat model
  próprios, e fica fora deste ADR.
- **O teto de 16 KiB é em bytes, os limites de 4096 por campo são em caracteres.** Texto e resposta
  longos com muito caractere não-ASCII (emoji, CJK) podem passar de 16 KiB e receber 413; com
  português, inglês e espanhol normais isso não ocorre. O fluxo do n8n corta por pontos de código
  para não partir um emoji ao meio.
- **Conversa duplicada na primeira mensagem.** `get_or_create_open_conversation` é um SELECT
  seguido de INSERT sem trava (código anterior a este ADR, o ingest o herda): duas primeiras
  mensagens do mesmo telefone com poucos milissegundos de diferença criam duas conversas abertas.
  Sem perda de dado nem status errado; fica como TD-N9.
- **Duas fontes do prompt** (backend e n8n) continuam até a 2c.
- **Áudio** segue ignorado pelo n8n até a 2b.
- Mudança no fluxo do n8n precisa ser exportada de novo para `docs/n8n/` na mesma entrega.

## Plano de adoção e reversão

1. Aprovação deste ADR pelo Patrick (feita em 2026-10-01, com os aceites de risco do
   [threat model](../threat-models/2026-10-01-ingestao-de-atendimentos-do-n8n.md)). Retenção
   (90 dias) e regra do status também já foram decididas.
2. Testes primeiro (TDD): `backend/tests/test_ingest_security.py` (segurança),
   `test_ingest.py` (comportamento), `test_purge_conversations.py` e `test_config.py`; todos
   falham antes do código.
3. Promover para públicos, no `message_handler.py`, os helpers de registro que o ingest reutiliza
   (`is_duplicate_delivery`, `store_incoming`), sem duplicar código (o gate mede duplicação).
4. Criar a rota, a variável `INGEST_API_TOKEN` (config, `deploy.yml`, `docs/deploy.md`), a rotina
   de expurgo de conversas com mais de 90 dias sem atividade (workflow diário
   `.github/workflows/retention.yml`, no lugar de agendamento no Cloud Run, para ficar no custo
   zero) e a atualização de `README.md` e `docs/n8n/README.md`.
5. Atualizar e reexportar o fluxo do n8n; teste de ponta a ponta com uma mensagem real no número +55
   e conferência no painel.
6. **Reversão:** remover o nó HTTP do fluxo (o endpoint fica inerte) e/ou apagar
   `INGEST_API_TOKEN` (a rota passa a responder 401). Nenhum dado nem migração para desfazer; as
   conversas já gravadas continuam no painel.

## Adendo (2026-10-03): nome do perfil do WhatsApp

Pedido do Patrick (tarefa do ClickUp "Painel: mostrar o nome do cliente quando estiver disponível"):
o painel mostra o nome do cliente, quando existe, no lugar do telefone. Mudança **aditiva**, sem
novo ADR, porque não troca nenhuma decisão acima:

- **Contrato:** `cliente_nome` **opcional** (texto de até 100 caracteres sem NUL, ou `null`) em
  `POST /api/ingest/atendimentos` e em `POST /api/ingest/mensagens`. Quem não manda o campo continua
  válido (retrocompatível). Ausente, nulo ou só espaços **mantém** o nome guardado; um nome novo
  substitui o anterior (o turista pode trocar o nome do perfil). O backend colapsa espaços e remove
  caracteres de controle antes de gravar. A resposta continua sem telefone nem nome.
- **Origem:** o n8n lê `contacts[0].profile.name` do gatilho do WhatsApp; o webhook antigo do
  backend lê `entry[].changes[].value.contacts[]` e casa `wa_id` com o `from` da mensagem.
- **Onde fica:** coluna `conversations.cliente_nome` (migração `0006`, nula nas conversas
  existentes), exposta como `cliente_nome` em `GET /api/conversations` e `GET /api/conversations/{id}`.
  Não há tabela de clientes: o nome vai e some com a conversa, então o expurgo de 90 dias o apaga
  junto. Uma conversa nova do mesmo telefone recebe o nome na próxima mensagem (a Meta o envia em
  toda entrega).
- **LGPD:** o nome é dado pessoal e texto do próprio turista (não confiável; o painel o renderiza
  como texto). Nunca vai a log, mensagem de erro (o 422 já não devolve valores), prompt do LLM nem
  resposta do n8n; testes em `backend/tests/test_customer_name.py` e `test_n8n_flow.py`.
