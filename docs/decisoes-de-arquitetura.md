# Decisões de arquitetura

Movido do `CLAUDE.md`. Não reabrir sem rodar o teste de qualidade documentado abaixo.

> **Atualização de 2026-10-01:** o [ADR-0004](adr/0004-n8n-orquestra-gemini-vertex-numero-de-producao.md)
> (Proposto) propõe orquestrar o atendimento no n8n e usar o Gemini no Vertex AI, o que **sai do
> custo zero** e substitui o Groq no fluxo de produção. Enquanto ele não for aprovado pelo Patrick,
> as decisões abaixo continuam sendo a regra do projeto. O teste de qualidade citado sobre o
> Gemini mediu a *API de desenvolvedor* (crédito pré-pago); o Vertex AI cobra por uso no billing
> do Google Cloud, que a Rovan já tem.

Decisão de arquitetura deliberada: **custo zero de infraestrutura**. Todo o stack roda nos
free tiers já usados em outros projetos Rovan (Cloud Run, Cloudflare Pages, Neon) mais o Groq
para o LLM. Por isso:

- **Groq** (`openai/gpt-oss-120b`) no lugar de hospedar um LLM local — evita cold start pesado
  no Cloud Run, que hiberna sem tráfego. Testado contra o Gemini API antes da decisão: o tier
  gratuito real do Gemini foi descontinuado (modelos atuais exigem crédito pré-pago), então
  Gemini não é usado neste projeto.
- **faster-whisper self-hosted** (modelo `base`, CPU) dentro do próprio backend — mensagens de
  voz do WhatsApp são curtas, então roda rápido mesmo sem GPU.
- **Sem LibreTranslate**: o teste de qualidade mostrou que o próprio Groq traduz bem sozinho
  (respostas nativas em pt/en/es), então uma camada extra de tradução seria redundante.
- **WhatsApp Business Cloud API oficial da Meta** (não Baileys/whatsapp-web.js): não arrisca
  banir o número real da agência e funciona via webhook, compatível com Cloud Run hibernando.
- **Não persistimos áudio bruto** — só a transcrição em texto. Minimiza dado sensível (LGPD) e
  evita precisar de storage de objeto (R2/S3), o que quebraria a meta de custo zero.
