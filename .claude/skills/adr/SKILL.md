---
name: adr
description: Cria um Architecture Decision Record em docs/adr/ (Contexto, Opções avaliadas, Decisão, Consequências positivas, Riscos/trade-offs) a partir do modelo do projeto. Use antes de qualquer mudança de banco, biblioteca de infraestrutura, padrão de comunicação, provedor de LLM ou estrutura de pastas (item GOV-1 do checklist).
argument-hint: "<título da decisão>"
disable-model-invocation: true
---

# /adr

Decisão: **$ARGUMENTS**

1. Leia `docs/adr/README.md`, `docs/adr/0000-modelo.md`, os ADRs existentes e
   `docs/decisoes-de-arquitetura.md` (não reabra decisões fixas sem o teste de qualidade).
2. Pesquise as opções no context7 e no código. Liste **pelo menos duas opções reais** mais "não
   fazer nada", com custo (custo zero é requisito) e riscos de cada uma.
3. Crie `docs/adr/NNNN-<slug>.md` (próximo número sequencial) com todas as seções do modelo e
   **Status: Proposto**. Acrescente a linha na tabela de `docs/adr/README.md`.
4. Apresente ao Patrick com a recomendação. **Não escreva código da decisão e não marque o ADR
   como `Aprovado`**: só o Patrick aprova. Depois da aprovação, atualize o status e siga o fluxo.
