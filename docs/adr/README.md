# Architecture Decision Records (ADR)

Toda mudança arquitetural significativa (banco de dados, nova biblioteca de infraestrutura, novo
padrão de comunicação, novo provedor de LLM, mudança de estrutura de pastas) **só começa depois de
um ADR aprovado aqui** (Manual V5 §2; item `GOV-1` do `docs/checklist-engenharia.md`).

- Crie com a skill `/adr <título>` ou copie `0000-modelo.md`. Numeração sequencial de 4 dígitos.
- Status: `Proposto` → `Aprovado` (pelo Patrick) → `Substituído por ADR-NNNN` ou `Rejeitado`.
  O agente **não** marca um ADR como `Aprovado` sozinho.
- Um ADR aprovado não é editado para mudar a decisão: escreva outro que o substitua.
- Decisões anteriores ao processo: `docs/decisoes-de-arquitetura.md`.

| ADR | Título | Status |
|---|---|---|
| [0001](0001-adocao-do-manual-v5.md) | Adoção do Manual Corporativo V5 e adaptações ao projeto | Aprovado |
