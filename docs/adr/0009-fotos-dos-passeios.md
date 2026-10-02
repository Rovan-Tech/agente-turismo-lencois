# ADR-0009: Fotos nos passeios, enviadas pela IA e pelo atendente

- **Status:** Aprovado (Patrick, 2026-10-01), com as opções recomendadas
- **Data:** 2026-10-01
- **Autores:** Patrick (requisito de produto); redação por Claude Code
- **Checklist afetado:** GOV-1, GOV-2, SEC-1, SEC-2, SEC-3, SEC-5, SEC-6, DATA-1, DATA-2, AI-1, AI-2, AI-3, INF-4
- **Depende de:** ADR-0008 (o backend envia mensagem pela Cloud API; sem isso não há como mandar foto
  pelo painel), ADR-0006 (login por pessoa) e ADR-0005 (o n8n pede ações ao backend).

## Contexto

Pedido do Patrick: cada passeio deve ter **fotos**, para o turista com dúvida poder **ver** o passeio,
e quem mostra é tanto **o atendente quanto a IA**.

Fatos, em 2026-10-01:

- O passeio hoje só tem texto e números (`tours`: nome, descrição, dificuldade, preço, capacidade).
  Não existe armazenamento de arquivo no projeto, e a decisão original de custo zero evitou storage
  de objeto (R2/S3) justamente para o áudio.
- O painel fica atrás do Cloudflare Access: um endereço dele **não serve** para a Meta baixar a
  imagem (a Meta busca por link público).
- A Cloud API da Meta aceita imagem por **link público** ou por **upload de mídia** (devolve um
  `media_id`, válido por cerca de 30 dias). Imagens: JPEG ou PNG, até 5 MB. Dentro da janela de 24 h
  da conversa não há cobrança.
- O Neon (plano gratuito) guarda 0,5 GB. Um catálogo de uns cinco passeios com cinco fotos cada,
  reduzidas a cerca de 300 KB, ocupa menos de 10 MB.
- O projeto já usa o Google Cloud (Cloud Run, Artifact Registry, Vertex AI) com cobrança ativa. A
  organização **bloqueia a criação de chave JSON de conta de serviço**, então o acesso ao Cloud
  Storage tem de ser pela identidade do serviço. O plano gratuito do Cloud Storage dá 5 GB de
  armazenamento, 5 mil operações de escrita e 50 mil de leitura por mês, **só em `us-central1`,
  `us-east1` e `us-west1`** (fonte: página de preços do Cloud Storage).
- O n8n escolhe o passeio sugerido (`passeio_sugerido_id`) e hoje responde só com texto; o backend
  é dono dos dados e, pelo ADR-0008, de enviar mensagens.
- A IA e o atendente precisam do mesmo comportamento (mesma lista de fotos, mesmo limite), então a
  regra deve morar num lugar só.

## Opções avaliadas

1. **Fotos num bucket privado do Cloud Storage, e o backend envia pelo upload de mídia da Meta**
   (recomendada; sugestão do Patrick). O backend valida e reencoda a foto (JPEG ≤ 1600 px, sem EXIF),
   guarda os **bytes no bucket** e só os **metadados no Neon** (`tour_photos`). Para enviar, baixa o
   objeto, sobe à Meta uma vez (guarda o `media_id` e a validade) e manda a imagem por ele. Prós: o
   projeto já roda no Google Cloud; o Cloud Run autentica **sem chave** (conta de serviço, o que a
   política da organização exige, já que bloqueia chave JSON); não consome o 0,5 GB do Neon; escala
   para mais fotos e vídeo; nenhuma foto fica pública. Custo zero **na região gratuita**: o plano
   gratuito do Cloud Storage cobre 5 GB, 5 mil operações de escrita e 50 mil de leitura por mês, mas
   só em `us-central1`, `us-east1` e `us-west1`. Contras: dependência nova (`google-cloud-storage`),
   configuração de permissão (IAM) que só o Patrick pode fazer, dois lugares a manter coerentes
   (banco e bucket), e uma região dos EUA no plano gratuito.
2. **Fotos no banco (Neon), com o mesmo envio pela Meta.** Zero infraestrutura nova, nenhuma
   permissão a configurar, volume pequeno (menos de 10 MB para uns cinco passeios). Contras: bytes no
   banco, dentro dos 0,5 GB gratuitos; não serve se o catálogo crescer ou entrarem vídeos.
3. **Cloudflare R2 com endereço público.** Sem custo de saída, mas o R2 pede forma de pagamento (a
   confirmar) e a foto fica num endereço público.
4. **Fotos versionadas no repositório, servidas por um projeto público do Pages.** Sem upload, mas a
   equipe da agência não troca foto sem um deploy, e a foto fica num endereço público.
5. **Não fazer nada.** A IA e o atendente só descrevem o passeio por texto.

## Decisão

Adotar a **opção 1** (Cloud Storage), com estas regras:

- **Armazenamento:** um bucket **privado** (acesso uniforme em nível de bucket e **prevenção de
  acesso público ativa**), em `us-central1` (plano gratuito). O Cloud Run acessa pela **conta de
  serviço do próprio serviço**, com o papel `roles/storage.objectUser` **só neste bucket**, sem chave
  JSON. Variável `PHOTOS_BUCKET`; sem ela, o recurso de foto fica desligado (fail-closed).
- **Acesso por uma interface** (`PhotoStorage`, com uma implementação do Cloud Storage e uma em
  memória para os testes): nenhuma regra de negócio conhece o Google.
- **Dados:** tabela `tour_photos` (`id`, `tour_id`, `ordem`, `objeto` (chave no bucket), `largura`,
  `altura`, `tamanho`, `sha256`, `legenda`, `meta_media_id`, `meta_media_expira_em`, `criada_por_sub`,
  `criada_em`). Teto de **5 fotos por passeio**, **5 MB por envio** e **60 fotos no total** (mantém
  o uso muito abaixo dos 5 GB e das cotas).
- **Ordem das gravações:** sobe o objeto (só cria, nunca sobrescreve) e **depois** grava a linha; ao
  apagar, tira a linha e **depois** apaga o objeto. Objeto órfão (falha no meio) é inofensivo e um
  comando de limpeza (`python -m app.purge_orphan_photos`) o remove.
- **Entrada pelo painel** (`POST /api/tours/{id}/fotos`, com login e `X-Panel-Request`): só JPEG,
  PNG ou WebP, conferidos pelo **conteúdo**; decodificadas e **reencodadas** como JPEG com Pillow
  (limite de pixels contra bomba de descompressão), o que remove EXIF e GPS e neutraliza arquivo
  disfarçado. SVG e outros formatos são recusados. Apagar e reordenar exigem login. O painel mostra
  as fotos por um endereço **autenticado** do backend (`GET /api/tours/fotos/{id}`), que lê do
  bucket e devolve os bytes: sem endereço assinado nem público.
- **Envio** (uma função do backend, usada pelos dois):
  - **Atendente:** botão "Enviar fotos" na conversa (em modo humano, ADR-0008): escolhe o passeio e
    as fotos, com legenda opcional.
  - **IA:** a saída do Gemini ganha `mostrar_fotos_passeio_id` (texto ou nulo). O n8n, depois da
    resposta em texto, chama o backend (`INGEST_API_TOKEN`) para enviar as fotos daquele passeio ao
    telefone da conversa. O catálogo que vai ao LLM ganha só `fotos` (a quantidade) por passeio; o
    `id` precisa estar nessa lista (lista de permitidos, como o `passeio_sugerido_id`). Se o bucket
    ou a Meta falhar, a IA segue só com o texto, sem erro para o turista.
  - **Regras comuns:** o destinatário é sempre o telefone da conversa; só dentro da janela de 24 h;
    no máximo **3 fotos por pedido** e **10 fotos por conversa por hora** (somando IA e atendente); a
    Meta recusando, nada é gravado; cada imagem enviada fica registrada como mensagem (`tipo =
    imagem`, `foto_id`, autor `ia` ou `atendente`) e aparece no painel como miniatura.
  - **Em modo humano a IA não envia foto** (a consulta do estado do ADR-0008 vale também aqui).
- **Direitos e privacidade:** só entram fotos que a agência pode usar (próprias ou com licença); fotos
  com **pessoas reconhecíveis** exigem autorização delas (LGPD), e como o bucket gratuito fica nos
  EUA, fotos com pessoas pedem a região do Brasil (ver Riscos). O formulário avisa. A demonstração
  pública (ADR-0007) usa ilustrações próprias, nunca as fotos reais.
- **Log:** só método, molde da rota, `sub` e resultado; nunca bytes, telefone nem token.

Decisões que dependem do Patrick estão em
[`docs/threat-models/2026-10-01-fotos-dos-passeios.md`](../threat-models/2026-10-01-fotos-dos-passeios.md).

## Consequências positivas

- O turista com dúvida vê o passeio, o que ajuda a vender.
- IA e atendente compartilham uma regra só, testada no repositório, com os mesmos limites.
- Nenhuma foto pública; custo zero dentro do plano gratuito do Cloud Storage; o banco guarda só
  metadados e fica longe do limite de 0,5 GB.
- EXIF e GPS saem das fotos que a equipe sobe.

## Riscos e trade-offs

- **Upload é superfície de ataque** (arquivo disfarçado, imagem enorme, tipo errado). Mitigação:
  validar pelo conteúdo, reencodar, teto de pixels, tamanho e quantidade.
- **Dois lugares para manter coerentes** (banco e bucket): a ordem das gravações e o comando de
  limpeza de órfãos limitam o problema; objeto sem linha é inofensivo, linha sem objeto vira erro
  tratado no envio e no painel.
- **Região dos EUA no plano gratuito:** fotos de passeio sem pessoas não são dado pessoal. Se a
  agência quiser fotos com pessoas, o bucket deve ficar em `southamerica-east1` (Brasil), que não está
  no plano gratuito, mas custa centavos por mês neste volume (menos de US$ 0,01); a regra de custo zero
  exigiria então uma decisão do Patrick.
- **Permissão (IAM) é configuração que só o Patrick faz:** criar o bucket, ativar a prevenção de acesso
  público e dar `roles/storage.objectUser` à conta de serviço do Cloud Run só nele (nunca no projeto
  inteiro).
- **Dependência nova:** `google-cloud-storage` (licença Apache-2.0), fixada e auditada.
- **Dependência nova (Pillow):** licença HPND, versão fixada, `pip-audit` limpo, e é uma biblioteca
  com histórico de CVEs de decodificação: precisa estar sempre atualizada (o Dependabot já cobre).
- **A IA pode pedir foto demais ou sem necessidade** (injeção de prompt ou erro do modelo): o teto
  por conversa e por pedido e a lista de passeios permitidos limitam o dano.
- **`media_id` da Meta expira** (cerca de 30 dias): o envio sobe a foto de novo quando a validade passou
  ou a Meta recusa o id.
- **Direito de imagem e licença das fotos** são responsabilidade de quem sobe; o painel só avisa.
- **Migração do banco** (nova tabela e colunas em `messages`): disputa o número com as migrações do
  agendamento e do atendimento humano.

## Plano de adoção e reversão

1. Aprovação deste ADR e do threat model pelo Patrick (feita em 2026-10-01, com as opções
   recomendadas: bucket privado do Cloud Storage em `us-central1` para fotos de passeio sem pessoas;
   a equipe sobe as fotos pelo painel; fotos da própria agência ou de licença livre, sempre sem
   pessoas reconhecíveis). A implementação vem depois do ADR-0008, que traz o envio.
2. O Patrick cria o bucket privado e dá a permissão à conta de serviço do Cloud Run (passos no
   `docs/deploy.md`), e eu confiro pela API, só leitura.
3. Testes primeiro (TDD), com o armazenamento em memória: upload (tipos, tamanho, conteúdo
   disfarçado, bomba de pixels, remoção de EXIF, limites), ordem das gravações e órfãos, envio
   (destinatário, janela de 24 h, tetos, falha da Meta ou do bucket sem gravar), a regra da IA (lista
   de permitidos, modo humano), autenticação e CSRF, e o painel.
4. Implementar: migração, Pillow, o cliente do Cloud Storage, rotas, serviço de envio compartilhado, saída do Gemini e fluxo do
   n8n, formulário e galeria no painel, botão "Enviar fotos".
5. Subir fotos reais ou de licença livre e testar de ponta a ponta: pedir fotos no WhatsApp (IA),
   assumir a conversa e enviar fotos pelo painel.
6. **Reversão:** desligar a chave da IA (a saída sem `mostrar_fotos_passeio_id` não envia nada),
   tirar `PHOTOS_BUCKET` (o recurso fecha) e `downgrade` da migração; o bucket e as fotos já enviadas
   continuam intactos.
