---
name: checklist
description: Autoverificação do diff contra o checklist de engenharia do projeto (docs/checklist-engenharia.md, Manual V5) antes de chamar o code-reviewer e o qa-tester. Lista cada item como OK, N/A ou FALHA com evidência e diz o que corrigir. Use ao terminar de implementar, dentro de /feature e /bugfix, ou quando pedirem "confere o checklist".
---

# checklist

Ensaio geral do que os agents vão cobrar. **Não substitui** o `code-reviewer` nem o `qa-tester`
(eles são independentes e refazem tudo), mas evita rodadas perdidas.

1. Leia `docs/checklist-engenharia.md` por inteiro. O escopo é o diff contra `origin/main`:
   `git diff $(git merge-base HEAD origin/main)` e `git ls-files --others --exclude-standard`.
2. Rode `python3 scripts/quality_gate.py --fast`.
3. Para **cada** item da matriz (reviewer e qa), decida e registre uma linha:
   `ID: OK — evidência` · `ID: N/A — fato que cumpre a condição da tabela` · `ID: FALHA — arquivo:linha`.
   - `OK` exige evidência concreta (comando, `arquivo:linha`, teste). Sem evidência, não é `OK`.
   - `N/A` só na condição objetiva da última coluna. Na dúvida, o item se aplica.
   - Itens ⏳ valem pelo que a coluna descreve; a lacuna de infraestrutura não é `FALHA`.
   - O que você não conseguiu verificar é `FALHA`.
   - Itens de execução (`qa`: E2E, Web Vitals, bundle, contraste) que você não rodou ficam como
     `pendente para o qa-tester`, nunca `OK`.
4. Mostre o resultado em tabela (ID · status · evidência) e a lista de `FALHA` com a correção.
5. Corrija as `FALHA` do escopo da tarefa (nunca afrouxando regra, limite, teste ou este checklist) e
   repita até zerar. Só então invoque os agents.
