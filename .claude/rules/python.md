---
paths:
  - "backend/**/*.py"
  - "scripts/**/*.py"
  - ".claude/hooks/**/*.py"
---

# Python (3.11)

Todas as regras valem para código **novo ou alterado**; o legado está em `docs/tech-debt.md`.
Ferramentas: `ruff` (lint+format, linha de 100), `mypy --strict`, `pytest`. O gate mede tudo.

## Sintaxe e tipos
- Sintaxe moderna do 3.11: `list[str]`, `X | None`, `dataclass(slots=True, frozen=True)`, `StrEnum`,
  `Protocol`, `TypedDict`, `Literal`, `Final`, `typing.override` (só 3.12: usar `typing_extensions`),
  `match` quando melhora a leitura.
- Tipagem completa em funções, métodos e atributos públicos. `Any` só com justificativa em comentário.
- `# type: ignore` só com código de erro e o porquê: `# type: ignore[arg-type]  # lib sem stubs`.
  ✅ `x: list[str] = []` · ❌ `x: List = []`

## Limites (medidos: ruff `C901`/`PLR0913`, `scripts/check_limits.py`)
- Função ≤ 40 linhas · complexidade ciclomática ≤ 10 · ≤ 5 parâmetros (acima, um objeto de
  parâmetros) · aninhamento ≤ 3 níveis · módulo ≤ 400 linhas.
- DRY: nenhum bloco duplicado com 6+ linhas (`jscpd`, config em `.jscpd.json`). Sem abstração
  prematura: nada de camadas ou classes "para o futuro".

## Design
- Responsabilidade única; funções pequenas e puras quando possível; composição em vez de herança.
- Injeção de dependência nas fronteiras (FastAPI `Depends`); sem estado global mutável.

## Erros e logs
- Exceções específicas, hierarquia própria do domínio, mensagem útil. Nunca `except:` nu nem
  exceção engolida (`except Exception: pass`).
- `logging` (nunca `print`), sem dado sensível (telefone, conteúdo de conversa, tokens, áudio).
- Timeout em toda chamada de rede (`httpx.AsyncClient(timeout=...)`).

## I/O e configuração
- `pathlib` e context managers. Config por variável de ambiente (`pydantic-settings`, já em
  `app/core/config.py`); nenhum segredo no código.

## Documentação
- **Docstrings Google em pt-BR** em módulos, classes e funções públicas (Args, Returns, Raises).
- Comentários explicam o **porquê**, nunca o quê; sem código comentado; TODO só com referência:
  `# TODO(#123): ...`. Isto substitui a antiga regra "sem docstrings".
- Nomes em **inglês** (código, commits); PEP 8; funções com verbo; booleanos `is_`/`has_`/`can_`.

## Imports
- Absolutos (`from app.services import x`); sem `import *`; sem import circular.

## Nunca
- Silenciar lint, tipo ou teste para passar no gate. Se a regra estiver errada, pergunte ao Patrick.
