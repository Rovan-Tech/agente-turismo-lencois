---
name: checklist
description: Consulta os itens de docs/checklist-engenharia.md (Manual V5) que a mudança atual aciona e aponta lacunas. Use quando pedirem "confere o checklist" ou em mudança de risco.
disable-model-invocation: true
---

# checklist

1. Veja o diff (`git diff $(git merge-base HEAD origin/main)`) e rode
   `python3 scripts/quality_gate.py --fast`.
2. Em `docs/checklist-engenharia.md`, leia só as seções que o diff aciona (ex.: `SEC`/`AI` se mexeu
   em webhook ou LLM; `FE` se mexeu no painel; `DATA` se mexeu em banco).
3. Liste em tabela só os itens acionados: `ID · OK|FALHA · evidência (arquivo:linha ou comando)`.
   Não liste os `N/A`.
4. Para cada `FALHA` do escopo da tarefa, proponha ou faça a correção mínima. Lacunas fora do escopo
   vão para `docs/tech-debt.md` em vez de bloquear a entrega.
