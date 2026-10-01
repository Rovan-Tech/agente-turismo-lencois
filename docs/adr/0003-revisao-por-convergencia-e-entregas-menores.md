# ADR-0003: Revisão por convergência, pré-voo obrigatório e entregas menores

- **Status:** Proposto
- **Data:** 2026-10-01
- **Autores:** Patrick / Claude Code
- **Checklist afetado:** `GOV-1`, `GOV-3`, `GIT-1`, `GATE-1`, `TEST-1`; `CLAUDE.md` (Fluxo obrigatório, passo 7) e as skills `/feature` e `/bugfix`

## Contexto

O fluxo obrigatório (`CLAUDE.md`) manda cada alteração passar pelo `code-reviewer` e pelo `qa-tester`,
com no máximo **3 rodadas por etapa**; se não convergir, para e explica o impasse. Na prática, as
entregas estouram o limite com frequência e o Patrick precisa autorizar rodadas extras.

O histórico de revisões deste repositório (`.claude/reports/`, 2026-09-30) mostra o seguinte:

| Entrega | Achados IMPORTANTE por rodada | Rodadas até aprovar |
| --- | --- | --- |
| Padrão V5 (hooks, checklist, rules) | 7 → 1 → 0 | 3 |
| Entrega seguinte | 14 → 8 → 4 → 2 → 0 | 5 (duas autorizadas à parte) |
| Pipeline de CI/CD (ADR-0002) | ~10 → 5 → 1 bloqueante | 4 (uma autorizada à parte) |
| Ajuste do Dependabot (PR #29) | 3 → 1 → 0 | 3 |

Em todas, os achados **diminuem a cada rodada**: o processo converge, e o limite de 3 corta uma
execução que estava terminando. Os achados são, em sua maioria, defeitos reais (um workflow que
reprovaria o próprio PR, uma regex que travaria o primeiro deploy, um agregador de checks que
anulava uma regra), e não ruído.

Causas que se repetem:

1. **Pré-requisitos do próprio fluxo pulados.** O passo 4 (gate rápido e `/checklist`
   autoverificado) e o ADR aprovado antes do código nem sempre acontecem; o revisor então gasta uma
   rodada em `FALHA` que o autor acharia sozinho (ex.: `GOV-1` por ADR ausente).
2. **Entregas grandes demais.** Dezenas de arquivos e várias fases numa revisão só: mais superfície,
   e cada correção abre superfície nova.
3. **Itens que não se resolvem no ambiente local.** "Não consegui verificar = `FALHA`" vale também
   para o que só roda no GitHub ou no GCP (deploy, CodeQL); e `GOV-1` espera aprovação humana, o que
   gasta uma rodada por motivo que não é técnico.
4. **O limite é por contagem, não por progresso.**

## Opções avaliadas

1. **Manter como está.** Simples, mas continua cortando entregas que convergem e treinando a
   autorização de rodada extra como rotina (o que esvazia o limite).
2. **Subir o limite para um número maior (5, 7).** Resolve o sintoma de hoje, mas sem critério:
   uma entrega que não converge consome o mesmo orçamento que uma que converge.
3. **Limite por convergência, pré-voo obrigatório e entregas menores (escolhida).** Ataca as quatro
   causas acima sem afrouxar nenhum item do checklist.
4. **Afrouxar o veredito** (aceitar `IMPORTANTE` ou "aprovado com ressalvas"). Rejeitada: contraria
   `GATE-4` e o ADR-0001; o problema não é rigor do revisor.

## Decisão

Adotar a opção 3, com quatro mudanças no fluxo:

1. **Limite por convergência.** O limite de 3 rodadas passa a valer só enquanto a contagem de achados
   (`FALHA` + BLOQUEANTE + IMPORTANTE) **não cai** de uma rodada para a seguinte. Enquanto cai, o fluxo
   segue, até um teto de **6 rodadas por etapa**. Se não cair em **2 rodadas seguidas**, ou ao chegar
   ao teto, para e explica o impasse ao Patrick (como hoje). Rodada extra deixa de depender de
   autorização caso a caso quando a regra está cumprida.
2. **Pré-voo obrigatório antes da 1ª rodada**, registrado no briefing do revisor: `/checklist`
   autoverificado sem `FALHA`; ADR e threat model aprovados quando exigidos; testes executados sobre o
   estado que será revisado (commit ou cópia equivalente, nunca só "no meu worktree sujo"); gate verde.
3. **Entregas menores.** Uma entrega por PR com um tema só; acima de cerca de **20 arquivos** ou de mais
   de uma fase, dividir antes de pedir revisão (o `code-reviewer` pode devolver o pedido por tamanho).
4. **Itens só verificáveis fora do ambiente local** (deploy no GCP, ferramentas que só rodam no
   GitHub) passam a exigir um **plano de verificação pós-merge** no PR e no relatório: o revisor
   avalia o plano e o raciocínio sobre o código, e o item não vira `FALHA` só por não ter sido
   executado. `N/A` continua só nas condições objetivas da tabela do checklist.

Nada disso muda o checklist, o critério "qualquer `FALHA` reprova" nem os limites de qualidade.

## Consequências positivas

- Entregas que convergem terminam sem negociação; as que não convergem param cedo, com o impasse
  explicado.
- Menos rodadas gastas em achados que o autor encontraria sozinho no pré-voo.
- Revisões menores são mais rápidas, e o revisor aprofunda em vez de varrer.

## Riscos e trade-offs

- **Mais rodadas por entrega** quando a regra de convergência permite continuar: custo em tempo e
  tokens. Mitigação: o teto de 6 e a regra de 2 rodadas sem queda.
- **Contar achados é grosseiro** (um BLOQUEANTE pesa como uma SUGESTÃO listada como IMPORTANTE).
  Mitigação: contar só `FALHA`, BLOQUEANTE e IMPORTANTE, e o revisor classificar com rigor.
- **Plano de verificação pós-merge pode virar atalho.** Mitigação: só vale para o que de fato não roda
  localmente; o revisor contesta a classificação; o PR registra quem confere depois do merge.
- **Editar `CLAUDE.md`, agents e skills de fluxo** é mudar a regra que protege o projeto. Por isso é
  ADR, com aprovação do Patrick. O limite de rodadas não está em hook (o portão do Stop só confere os
  vereditos), então nenhum hook muda por causa dele.

## Plano de adoção e reversão

- Após a aprovação: atualizar `CLAUDE.md` (passo 7 e "Briefing dos subagents"), `.claude/agents/*.md`
  (pré-voo e plano de verificação) e as skills `/feature` e `/bugfix` (item "Limite"), mais os testes
  em `backend/tests/tooling/` que conferirem esses textos. Cada mudança com teste.
- Medir nas três entregas seguintes: rodadas até aprovar e achados por rodada em `.claude/reports/`.
  Se a média de rodadas não cair, revisar este ADR.
- Reversão: restaurar o passo 7 original (3 rodadas fixas); nada de dado a migrar.
