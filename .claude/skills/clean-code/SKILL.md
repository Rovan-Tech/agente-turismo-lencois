---
name: clean-code
description: Remove comentários redundantes, código comentado e TODOs sem referência do código alterado (backend Python e frontend TS/TSX), preservando docstrings Google em pt-BR e diretivas funcionais (# noqa, # nosec, # type:, eslint-disable, /// <reference). Roda o gate rápido depois. Use ao terminar uma tarefa, dentro do /prepare-pr, ou quando pedirem "limpa o código".
---

# clean-code

Regra do projeto (`.claude/rules/python.md`): **docstrings Google em pt-BR nos símbolos públicos;
comentários só explicam o porquê**. Esta skill tira o que sobra, não a documentação.

## O que remove (só no código alterado)

- Comentários que repetem o que o código já diz (`# incrementa i`), código comentado e `TODO` sem
  referência (`TODO(#123)` é válido).
- Python: comentários `#` óbvios e docstrings **vazias ou que só repetem a assinatura**.
- TypeScript/TSX: comentários `//`, `/* */` e JSDoc equivalentes, incluindo `{/* */}` em JSX.

## O que NÃO remove

- Docstrings Google em pt-BR de módulos, classes e funções públicas (Args, Returns, Raises).
- Comentários de **porquê** (decisão não óbvia, ex.: por que não persistimos áudio bruto).
- Diretivas funcionais: `# noqa[...]`, `# nosec`, `# type: ignore[...]`, `# pragma: no cover`,
  shebang, `// @ts-expect-error`, `/// <reference types="..." />`, `eslint-disable`.
- A string `description=` do FastAPI e textos exibidos ao usuário.
- `CHANGELOG`, `README.md`, `CLAUDE.md`, `docs/`.

## Passo a passo

1. Escopo: arquivos alterados (`git diff --name-only $(git merge-base HEAD origin/main)`).
2. Edite manualmente (nunca regex no arquivo inteiro: JSX, strings e union types quebram).
3. Confirme: `python3 scripts/quality_gate.py --fast` (formatação, lint, tipos, limites).
4. Reporte quantos arquivos mudaram. Não abra PR sozinho.
