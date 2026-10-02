# ADR-0007: Publicar uma demonstração do painel, sem backend, e manter o painel real privado

- **Status:** Aprovado (Patrick, 2026-10-01)
- **Data:** 2026-10-01
- **Autores:** Patrick (requisito de produto); redação por Claude Code
- **Checklist afetado:** GOV-1, GOV-2 (N/A justificado abaixo), SEC-6, FE-4, FE-5, INF-3, INF-4, TEST-3

## Contexto

O projeto é uma peça de **portfólio da Rovan**: serve para atrair clientes de turismo. O Patrick
definiu o que ele precisa ter:

1. **Uma demonstração que qualquer pessoa pode abrir**, só para ver como funciona. Não salva nada.
2. **A versão real, a atual**, que a pessoa conhece entrando em contato (pelo WhatsApp da
   agência); a Rovan demonstra o painel real em conversa.

Fatos, em 2026-10-01:

- O painel real guarda conversas e telefones de turistas de verdade (LGPD) e hoje abre sem login.
  O ADR-0006 o coloca atrás do Cloudflare Access: ele passa a ser **privado**, para a equipe.
- Um painel público que lesse o backend real expõe dado de pessoas. Um painel público que
  escrevesse no backend real deixaria qualquer visitante poluir o banco e consumir a cota gratuita.
- O frontend já usa uma camada única de acesso à API (`lib/api.ts`, com validação por Zod), o que
  permite trocar a origem dos dados sem mudar as telas.
- O número de WhatsApp da agência é um canal comercial público por natureza, mas cada mensagem
  consome Gemini e execuções do n8n (cerca de 5 por mensagem; plano com 2.500 por mês, TD-N8).
- Custo zero é requisito.

## Opções avaliadas

1. **Modo demonstração no mesmo frontend, sem backend.** Uma variável de build
   (`VITE_DEMO=true`) troca `lib/api.ts` por uma implementação em memória, com dados fictícios, e
   o resultado é publicado como **outro projeto do Cloudflare Pages**. As telas são as reais, então
   a demonstração mostra o produto de verdade. Prós: interativa (abrir conversas, mudar status,
   ver passeios e vagas), sem servidor, sem banco, sem segredo, sem custo, sem dado pessoal,
   recarregar reinicia tudo. Contras: precisa manter as fixtures e garantir que a demonstração
   não se afaste do produto.
2. **Vídeo ou capturas de tela.** Risco zero e fácil, mas não é interativa e envelhece. Serve como
   complemento, não como a amostra.
3. **Backend de demonstração separado** (outro Cloud Run e outro Neon, com dados fictícios e
   escrita aberta). Interativa e com o fluxo real, mas os dados passam a persistir, qualquer um
   escreve, a cota gratuita está exposta a abuso e há mais uma infraestrutura para vigiar.
4. **Abrir o painel real em modo somente leitura.** Descartada: expõe dado real.

## Decisão

Adotar a **opção 1**, com o painel real privado (ADR-0006) e a **opção 2 como complemento**.

- **Modo demonstração:** `VITE_DEMO=true` troca a camada de dados por `demoApi`, 100% em memória.
  Sem rede, sem `localStorage`, `sessionStorage`, IndexedDB ou cookies: "não salva nada" vale ao
  pé da letra, e recarregar a página volta ao começo. As ações funcionam só na tela (marcar como
  resolvida, mudar status, ver e editar passeios e, desde o ADR-0008, assumir a conversa, responder
  e devolver à IA: o turista da demonstração responde uma vez sozinho para a tela mostrar a releitura).
- **Dados 100% fictícios:** nomes inventados e telefones de uma faixa **inexistente** (DDD `00`,
  por exemplo `+55 00 90000-0001`). Um teste falha se alguma fixture tiver telefone fora desse
  padrão, para nenhum número real entrar na demonstração.
- **Identificação clara:** uma faixa fixa no topo, "Demonstração com dados fictícios. Nada é
  salvo.", com o botão **"Conversar com o assistente de verdade"**, que abre o WhatsApp do número
  da agência (`wa.me`). É o caminho para a pessoa entrar em contato; o painel real é mostrado pela
  Rovan numa conversa.
- **Publicação separada:** um segundo projeto do Cloudflare Pages (nome sugerido
  `agente-turismo-lencois-demo`), com um job próprio no `deploy.yml` que **não recebe** `DATABASE_URL`
  nem token algum, só as credenciais de publicação do Cloudflare. O build da demonstração não
  inclui `VITE_API_BASE_URL` nem token.
- **Isolamento verificável:** um `_headers` emitido pelo build de demonstração (plugin em
  `frontend/demo/vitePlugin.ts`, com o hash do script inline do tema) com CSP `default-src
  'self'` e `connect-src 'none'` (o navegador recusa qualquer chamada de rede), e um teste no CI
  que procura no pacote publicado o endereço do Cloud Run, `run.app` e padrões de token.
- **Funções futuras na demonstração:** só entram quando existirem de verdade no produto; uma
  prévia de algo ainda não pronto precisa vir marcada como "em breve".
- **No portfólio da Rovan** (repositório `rovan-tech`, fora deste), a página do projeto aponta
  para a demonstração e para o contato. Essa mudança é um PR separado, naquele repositório.
- **GOV-2 (threat model):** N/A por esta decisão: a demonstração não tem endpoint, não trata dado
  pessoal e não chama LLM (não há backend). A superfície que sobra (fixtures sem dado real e pacote
  sem segredo) tem teste automatizado, descrito acima. O painel real segue sob o ADR-0006.

## Consequências positivas

- A Rovan passa a ter uma vitrine interativa, aberta a qualquer visitante, sem nenhum dado real
  nem risco de abuso do backend.
- O painel real fica privado e pode guardar conversas de verdade com segurança.
- A demonstração usa as mesmas telas do produto: o que o visitante vê é o que o cliente recebe.
- Custo zero adicional (Pages gratuito, sem servidor).

## Riscos e trade-offs

- **A demonstração pode se afastar do produto** quando uma tela mudar. Mitigação: as telas são as
  mesmas; a E2E da demonstração roda no CI.
- **Manutenção das fixtures** (conversas, passeios, vagas). Mitigação: uma única fonte, em um
  arquivo, validada por Zod com os mesmos schemas do produto.
- **O WhatsApp público atrai mensagens de teste e spam:** cada uma gasta Gemini e execuções do n8n
  (cerca de 500 mensagens por mês no plano atual), e as conversas de quem escrever aparecem no
  painel real, com telefone, por 90 dias. **Antes de divulgar o número em destaque**, é preciso
  alerta de orçamento e limite de uso (TD-N8, TD-A3) e uma primeira resposta com aviso de
  privacidade. Este ADR **não** divulga o número: só prevê o botão.
- **A demonstração mostra um painel de equipe:** não deve sugerir que o visitante está vendo o
  sistema de produção (daí a faixa fixa).

## Plano de adoção e reversão

1. Aprovação deste ADR pelo Patrick (feita em 2026-10-01, junto com a do ADR-0006).
2. Testes primeiro (TDD): `demoApi` sem acesso à rede ou a armazenamento, fixtures sem telefone
   real, pacote publicado sem endereço de backend nem token, faixa de demonstração visível, E2E do
   fluxo (abrir conversa, mudar status, ver passeios).
3. Implementar o modo demonstração, o script de build, o segundo projeto no Pages e o job de
   deploy. **Estado (2026-10-01):** modo, build e job implementados; o projeto do Pages será criado
   no primeiro deploy depois do merge e `DEMO_WHATSAPP` segue sem definir.
4. Atualizar `README.md`, `docs/deploy.md` e `docs/design-system.md` (faixa de demonstração).
5. PR no repositório `rovan-tech` com a página do projeto.
6. **Reversão:** desativar o job e apagar o projeto do Pages. A demonstração não toca no produto
   nem em dados, então não há nada a desfazer além do link no portfólio.
