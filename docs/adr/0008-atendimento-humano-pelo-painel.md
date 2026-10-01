# ADR-0008: Permitir que uma pessoa assuma a conversa no painel e responda no lugar da IA

- **Status:** Aprovado (Patrick, 2026-10-01), com as opções recomendadas
- **Data:** 2026-10-01
- **Autores:** Patrick (pedido); redação por Claude Code
- **Checklist afetado:** GOV-1, GOV-2, SEC-1, SEC-3, SEC-6, DATA-1, DATA-2, DATA-3, OBS-1, AI-3, TEST-3
- **Depende de:** ADR-0006 (login por pessoa, já em produção), ADR-0005 (ingest do n8n) e ADR-0004.

## Contexto

Fatos, em 2026-10-01:

- O painel só **lê** as conversas e marca como resolvida. Quando a IA marca "precisa de atenção",
  a equipe não tem como responder pelo painel: teria de usar o app do WhatsApp Business por fora, e a
  IA continuaria respondendo por cima.
- O envio de WhatsApp já existe no backend (`services/whatsapp_client.send_text_message`, com
  timeout de 15 s), mas os `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID` do deploy são da **conta de
  teste antiga**. O atendimento de hoje roda no n8n, com a credencial do número +55 de produção.
- O painel agora exige login por pessoa e o backend sabe quem agiu (`sub` do JWT, ADR-0006): é o que
  este recurso precisa para enviar mensagem **como a agência** com segurança e registrar quem
  respondeu.
- O n8n responde a **toda** mensagem recebida. Hoje ele não consulta o backend sobre o estado da
  conversa (só lê o catálogo e grava o atendimento depois).
- A Meta só aceita texto livre até **24 horas** depois da última mensagem do turista; depois disso
  exige um modelo de mensagem aprovado (erro `131047`).
- A migração do banco que este recurso exige (colunas novas em `conversations` e `messages`)
  disputa o número com a `0004` do agendamento, que está em outra branch e ainda não foi mergeada.
- Custo zero é requisito; as mensagens dentro da janela de 24 h não são cobradas pela Meta.

## Opções avaliadas

1. **O backend envia direto pela Cloud API e o n8n consulta o estado da conversa** (recomendada).
   O painel chama `POST /api/conversations/{id}/mensagens`; o backend confere a regra, envia pela
   Cloud API, grava a mensagem como "atendente" e devolve o resultado. O n8n pergunta ao backend,
   antes de chamar o Gemini, se a conversa está com humano. Prós: reaproveita o cliente existente,
   a regra e o erro da Meta ficam no código testado do repositório, sem dependência de uma execução
   do n8n por mensagem. Contras: o token da Meta passa a existir também no GitHub e no Cloud Run
   (um segundo lugar além do n8n).
2. **O backend pede ao n8n para enviar** (um fluxo "Enviar mensagem do atendente", com gatilho
   webhook). O token da Meta continua só no n8n. Contras: uma execução do n8n por mensagem (plano
   de 2.500 por mês), mais uma dependência e um novo segredo backend→n8n, e o erro da Meta e a
   janela de 24 h voltam ao backend por um caminho a mais para tratar.
3. **O atendente responde pelo app do WhatsApp Business e o painel só silencia a IA.** Barato, mas a
   resposta não passa pelo painel (sem registro de quem respondeu, sem histórico no painel) e a
   Cloud API não permite o mesmo número no app e na API ao mesmo tempo sem a coexistência da Meta.
4. **Não fazer nada.** A equipe não consegue assumir; "precisa de atenção" só avisa.

## Decisão

Adotar a **opção 1**, com estas regras:

- **Estado da conversa:** `conversations.atendimento` (`ia` ou `humano`, padrão `ia`), mais
  `humano_sub` (quem assumiu), `humano_nome` (o nome mostrado ao turista) e `humano_desde`. O botão
  **"Assumir conversa"** muda para `humano` e **"Devolver para a IA"** volta para `ia`. Marcar a
  conversa como **resolvida** também devolve à IA.
- **Aviso ao turista ao assumir** (pedido do Patrick): assim que a pessoa assume, o turista recebe
  uma mensagem avisando que **agora quem fala é uma pessoa da equipe, com o nome dela**, no idioma da
  conversa (pt, en ou es; sem idioma detectado, trilíngue). Exemplo em português: "Olá! Agora quem
  está falando com você é uma pessoa da nossa equipe: Patrick. Pode continuar por aqui." O texto é
  fixo (modelo), nunca digitado, e fica gravado como mensagem do atendente.
  - **O nome vem do login**, nunca do corpo da requisição: é o claim `name` do JWT do Access, se
    houver, ou o **primeiro nome derivado do e-mail** do JWT verificado (`patrick.fernandes@…` vira
    "Patrick"). Só letras, até 30 caracteres; se não sobrar um nome (e-mail como `contato@` ou com
    números), o aviso diz só "uma pessoa da nossa equipe". **O e-mail não é gravado, logado nem
    enviado ao turista**: só o primeiro nome derivado.
  - **Ordem:** o aviso é enviado **antes** de mudar o estado. Se a Meta recusar (por exemplo, janela
    de 24 h fechada), a conversa **não** muda para `humano` e a pessoa vê o motivo. Assumir de novo
    uma conversa que já está com a mesma pessoa não reenvia o aviso; se estiver com outra pessoa, é
    409 ("já está com <nome>"): para trocar, quem está atendendo devolve primeiro.
- **Mensagens:** `messages.autor` (`turista`, `ia` ou `atendente`) e `messages.autor_sub` (a pessoa,
  só para `atendente`; vale também para o aviso de que assumiu) e `messages.client_message_id` (único), gerado pelo painel para **o envio ser
  idempotente** (clique duplo ou nova tentativa não manda duas vezes).
- **Envio** (`POST /api/conversations/{id}/mensagens`, protegido pelo login do ADR-0006 e pelo
  cabeçalho `X-Panel-Request`): o destinatário é **sempre o telefone da própria conversa**, nunca um
  campo do corpo; só vale se a conversa estiver em `humano`; texto de 1 a 4096 caracteres (sem NUL,
  como no ingest); no máximo 60 mensagens de atendente por conversa por hora; **recusa com 409 se a
  última mensagem do turista tem mais de 24 horas** (o painel desabilita o campo e explica). O envio
  vem **antes** da gravação: se a Meta recusar, nada fica gravado e o atendente vê o motivo, sem
  telefone nem token.
- **IA pausada:** o n8n passa a chamar `POST /api/ingest/conversas/atendimento`
  com o telefone no **corpo** (`INGEST_API_TOKEN`; na URL o telefone cairia no log de acesso) antes de gerar a resposta. Com a conversa em `humano`, o n8n **só registra**
  a mensagem do turista (rota de ingest só de entrada) e **não responde**. Se a consulta falhar, o
  fluxo cai na contingência (nunca responde "no escuro" por cima de um humano).
- **Devolução automática:** depois de `HUMAN_HANDOFF_IDLE_HOURS` (padrão **2**) sem mensagem do
  atendente, a conversa volta para a IA, para o turista nunca ficar sem resposta porque alguém
  esqueceu de devolver. O fluxo do n8n é quem pergunta, então a regra vale no momento da pergunta
  (sem tarefa agendada nova).
- **Painel:** botões "Assumir conversa" e "Devolver para a IA", campo de resposta com contador e o
  aviso da janela de 24 h, selo "Você está atendendo" no lugar de "Assistente de IA respondendo
  agora", marca "atendente" nas mensagens, e a tela da conversa **atualiza sozinha a cada 15 s**
  enquanto estiver em `humano` (hoje não há atualização, e o atendente precisa ver o que o turista
  escreve). O texto da lateral ("o assistente também atualiza o status…") é corrigido.
- **Segredos:** `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID` de **produção** nos secrets do GitHub
  (feito por quem tem o token da Meta, nunca no repositório nem na conversa).
- **Concorrência:** assumir, devolver e enviar travam a linha da conversa (`SELECT … FOR UPDATE`) e
  reavaliam o estado depois da trava, então dois cliques ou duas pessoas ao mesmo tempo não mandam
  dois avisos: o segundo vira "mesma pessoa" (200, sem reenviar) ou 409.
- **Log:** só método, molde da rota, `sub` e o resultado; nunca texto, telefone nem token.

Decisões que dependem do Patrick estão em
[`docs/threat-models/2026-10-01-atendimento-humano.md`](../threat-models/2026-10-01-atendimento-humano.md).

## Consequências positivas

- A equipe responde pelo painel, com histórico único e registro de quem respondeu.
- A IA nunca fala por cima de uma pessoa, e uma conversa esquecida volta sozinha para a IA.
- Reaproveita o login por pessoa, o ingest e o cliente do WhatsApp; custo zero adicional.
- A regra da janela de 24 h e os erros da Meta ficam no código testado.

## Riscos e trade-offs

- **O token de produção da Meta passa a existir em mais um lugar** (GitHub e Cloud Run). Se vazar,
  vale enviar mensagens como a agência. Mitigação: rotacionar o token do usuário do sistema, escopo
  só de mensagens, e a opção 2 evitaria o risco ao custo de uma execução do n8n por mensagem.
- **Mexe no fluxo ativo do n8n** (consulta do estado e rota de só entrada): mudança em produção, com
  versão anterior no histórico do n8n para reverter.
- **O nome da pessoa vai a um terceiro (o turista):** só o primeiro nome, derivado do e-mail do
  login, e a pessoa fica sabendo disso ao assumir (o painel mostra "o turista verá: Patrick"). Se o
  e-mail não der um nome razoável, o aviso sai sem nome.
- **Migração do banco:** cinco colunas em `conversations`, três em `messages`. O número da migração
  depende de a `0004` do agendamento ser mergeada antes; se não for, a nossa vira `0004` e a do
  agendamento precisa ser renumerada (cabeçalhos múltiplos do Alembic). Reversível (`downgrade`
  testado).
- **Corrida humano × IA:** uma mensagem do turista que chega no instante em que o atendente assume
  pode ser respondida pela IA uma última vez. Aceito e raro.
- **Entrega e gravação não são atômicas:** se a Meta aceitar a mensagem e a gravação falhar (ou o
  tempo esgotar com a mensagem já entregue), a nova tentativa reenvia e o turista pode receber a
  mesma mensagem duas vezes. Não há outbox; aceito pelo volume baixo.
- **A trava espera a Meta:** a linha da conversa fica travada até 15 s durante o envio, e a gravação
  de mensagem do n8n na mesma conversa (por causa da chave estrangeira) espera junto. Sem deadlock,
  e a espera só vale dentro de uma conversa.
- **Sem aviso em tempo real:** o atendente só vê a mensagem nova quando a tela atualiza (15 s) ou ele
  abre o painel. Notificação (e-mail, push) fica fora deste ADR.
- **Sem limite de taxa geral (TD-A3):** o teto de 60 mensagens por conversa por hora limita o dano de
  um login comprometido ou de um erro, mas não a quantidade de conversas.
- **Qualquer pessoa autorizada pode assumir qualquer conversa** (sem papéis, como no ADR-0006).

## Plano de adoção e reversão

> **Entrega em duas partes.** O PR 1 (#55) é o backend. O PR 2 traz o painel (botões, campo de
> resposta, aviso da janela de 24 h, atualização a cada 15 s) e o fluxo do n8n **exportado**; o
> fluxo em produção é publicado à mão no n8n (passo 5). **Até lá, assumir a conversa não silencia a
> IA**: a equipe não deve ser orientada a usar antes. Desvio: a lateral global "Assistente de IA
> respondendo agora" não mudou (vale para o sistema todo); o estado por conversa aparece no painel
> lateral da conversa e na lista ("Atendendo: nome").

1. Aprovação deste ADR e do threat model pelo Patrick (feita em 2026-10-01, com as opções
   recomendadas: o backend envia; só o primeiro nome no aviso; aviso curto ao devolver para a IA;
   devolução automática após 2 horas; teto de 60 mensagens por conversa por hora; a migração desta
   entrega é a `0004`, e a do agendamento da Leandro passa a `0005` quando for mergeada).
2. O Patrick coloca `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID` de produção nos secrets do GitHub.
3. Testes primeiro (TDD): estado e transições, envio (destinatário só da conversa, janela de 24 h,
   idempotência, teto por hora, falha da Meta sem gravar), consulta do n8n, devolução automática,
   login e CSRF, e o painel (botões, campo, aviso, atualização).
4. Implementar: migração Alembic, serviço e rotas, ingest do n8n, painel e documentação.
5. Atualizar o fluxo ativo do n8n (consulta do estado e rota de só entrada), publicar, e testar com
   uma mensagem real: assumir, responder pelo painel, ver chegar no WhatsApp e devolver à IA.
6. **Reversão:** o backend aceita estado `ia` para todas as conversas, então voltar o fluxo do n8n
   para a versão anterior e `downgrade` da migração desfaz tudo; as mensagens de atendente já
   enviadas continuam no histórico.
