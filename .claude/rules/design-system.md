---
paths:
  - "frontend/src/**"
  - "frontend/index.html"
  - "frontend/tailwind.config.js"
  - "docs/design-system.md"
---

# Design system

Fonte única: `frontend/src/styles/tokens.css`. Guia legível: `docs/design-system.md`.
Verificado por `scripts/check_design_tokens.py` (gate + hook).

## Cores em duas camadas
1. Paleta base `--palette-{primary,secondary,neutral,success,warning,error,info}-{50..900}`.
2. Semânticos `--color-*` (ex.: `--color-text-primary`, `--color-bg-surface`,
   `--color-action-primary`). **Componentes usam só semânticos**, via classes do Tailwind:
   ✅ `bg-surface text-primary border-subtle` · ❌ `bg-white`, `text-gray-500`, `#0F7A8C`.
- Hex/rgb/hsl só em `tokens.css`. O modo escuro redefine só os semânticos.
- Sem `opacity-*`/`/60` para "clarear" texto (derruba o contraste): use `text-muted`/`text-secondary`.
- Precisa de uma cor nova? Adicione o token (paleta → semântico) e rode o verificador de contraste.

## Tipografia
Inter (texto), Sora (títulos `h1`–`h3`), JetBrains Mono (mono), sempre via `font-sans`/`font-display`/
`font-mono`, com fallback de sistema e `display=swap`. Pesos: 400, 500, 600, 700.

## Espaçamento e forma
Escala de 4 px (`0,1,2,3,4,5,6,8,10,12,16`); raios `sm/md/lg/full`; sombras `sm/md/lg`; z-index e
durações por token. Mobile-first: estilo base = celular; `sm:`/`md:`/`lg:` ampliam.

## Acessibilidade (WCAG 2.2 AA)
- Contraste ≥ 4,5:1 (texto normal) e ≥ 3:1 (texto grande, componentes, anel de foco).
- Foco sempre visível (`:focus-visible` global); tudo operável por teclado; `alt` em imagens;
  `<label>` em todo campo; estado **nunca só por cor** (o `StatusBadge` sempre traz texto).

## Estados
Todo componente interativo/de dados cobre: hover, focus, active, disabled, carregando, erro, vazio.
