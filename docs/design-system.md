# Design system — Painel Agente de Turismo Lençóis

Fonte única: [`frontend/src/styles/tokens.css`](../frontend/src/styles/tokens.css). Este documento é o guia legível; as regras verificáveis estão em [`.claude/rules/design-system.md`](../.claude/rules/design-system.md) e o contraste é validado por `scripts/check_design_tokens.py` (rodado no gate).

## Como usar

Componentes usam **só tokens semânticos**, expostos como classes do Tailwind (`tailwind.config.js`):

```tsx
// ✅ semântico: muda sozinho no tema escuro
<div className="rounded-lg border border-subtle bg-surface text-primary" />

// ❌ cor literal ou paleta padrão do Tailwind
<div className="bg-white text-gray-900 border-[#ddd]" />
```

Cores literais (hex/rgb/hsl) só existem em `tokens.css`. Um hook e o gate acusam qualquer uso fora dele.

## Paleta base (camada 1)

Âncoras da marca: **primary-600** = lagoa `#0F7A8C`, **secondary-700** = terracota `#9C5227`, **neutral-50** = areia `#FDFBF6`, **neutral-900** = grafite `#1F2A2E`.

| Escala    | 50        | 100       | 200       | 300       | 400       | 500       | 600       | 700       | 800       | 900       |
| --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- |
| primary   | `#f1f7f8` | `#cbe2e6` | `#a5cdd4` | `#80b9c2` | `#5aa4b0` | `#358f9e` | `#0f7a8c` | `#0d5d6b` | `#0b4049` | `#0a2328` |
| secondary | `#f9f5f2` | `#ecddd5` | `#dec6b8` | `#d1af9b` | `#c4987e` | `#b78061` | `#a96944` | `#9c5227` | `#62361c` | `#291a12` |
| neutral   | `#fdfbf6` | `#e4e4e0` | `#cccdca` | `#b3b5b3` | `#9a9e9d` | `#828787` | `#697071` | `#50585a` | `#384144` | `#1f2a2e` |
| success   | `#f2f7f3` | `#cee2d5` | `#abcdb6` | `#88b998` | `#64a479` | `#418f5b` | `#1e7a3c` | `#185d30` | `#134023` | `#0d2317` |
| warning   | `#faf5f0` | `#efdaca` | `#e3bfa3` | `#d7a47d` | `#cc8956` | `#c06e30` | `#b45309` | `#87400a` | `#5b2d0b` | `#2e1a0b` |
| error     | `#fbf3f2` | `#f1d3d1` | `#e7b4b0` | `#de948f` | `#d4756e` | `#ca554d` | `#c0362c` | `#902b24` | `#601f1b` | `#301413` |
| info      | `#f2f6fa` | `#d0ddec` | `#aec5df` | `#8bacd1` | `#6994c3` | `#477bb6` | `#2563a8` | `#1d4c7f` | `#163557` | `#0e1e2e` |

`neutral-0` = `#FFFFFF` (superfícies claras).

## Tokens semânticos (camada 2)

| Token                           | Claro     | Escuro    | Uso                                               |
| ------------------------------- | --------- | --------- | ------------------------------------------------- |
| `--color-bg-page`               | `#fdfbf6` | `#1f2a2e` | fundo da página                                   |
| `--color-bg-surface`            | `#ffffff` | `#384144` | cartões, listas, balões recebidos                 |
| `--color-bg-subtle`             | `#f1f7f8` | `#0a2328` | hover de linhas                                   |
| `--color-bg-header`             | `#0f7a8c` | `#0b4049` | cabeçalho                                         |
| `--color-text-primary`          | `#1f2a2e` | `#fdfbf6` | texto principal e títulos                         |
| `--color-text-secondary`        | `#50585a` | `#cccdca` | texto de apoio                                    |
| `--color-text-muted`            | `#697071` | `#b3b5b3` | metadados, estados vazio/carregando               |
| `--color-text-link`             | `#0d5d6b` | `#80b9c2` | links                                             |
| `--color-text-on-action`        | `#ffffff` | `#1f2a2e` | texto sobre ação primária/secundária              |
| `--color-text-on-header`        | `#ffffff` | `#ffffff` | texto do cabeçalho                                |
| `--color-action-primary`        | `#0f7a8c` | `#5aa4b0` | botões e balões enviados                          |
| `--color-action-primary-hover`  | `#0d5d6b` | `#80b9c2` | hover da ação primária                            |
| `--color-action-primary-active` | `#0b4049` | `#a5cdd4` | active da ação primária                           |
| `--color-action-secondary`      | `#9c5227` | `#d1af9b` | destaque de atenção (terracota)                   |
| `--color-border-subtle`         | `#e4e4e0` | `#50585a` | divisores e bordas de cartão                      |
| `--color-border-strong`         | `#828787` | `#9a9e9d` | bordas de campos (≥ 3:1)                          |
| `--color-focus-ring`            | `#0f7a8c` | `#80b9c2` | anel de foco                                      |
| `--color-border-attention`      | `#9c5227` | `#d1af9b` | borda esquerda das conversas que precisam de atenção |
| `--color-indicator-online`      | `#1e7a3c` | `#88b998` | ponto do indicativo "Assistente de IA respondendo" |
| `--color-accent-subtle-bg`      | `#cbe2e6` | `#0b4049` | selo "Aberta"                                     |
| `--color-accent-subtle-fg`      | `#0b4049` | `#cbe2e6` | texto do selo "Aberta"                            |
| `--color-neutral-subtle-bg`     | `#e4e4e0` | `#50585a` | selo "Resolvida"                                  |
| `--color-neutral-subtle-fg`     | `#384144` | `#e4e4e0` | texto do selo "Resolvida"                         |
| `--color-status-success-bg`     | `#f2f7f3` | `#0d2317` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-success-fg`     | `#134023` | `#cee2d5` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-warning-bg`     | `#faf5f0` | `#2e1a0b` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-warning-fg`     | `#5b2d0b` | `#efdaca` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-error-bg`       | `#fbf3f2` | `#301413` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-error-fg`       | `#601f1b` | `#f1d3d1` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-info-bg`        | `#f2f6fa` | `#0e1e2e` | estados de feedback (sucesso, alerta, erro, info) |
| `--color-status-info-fg`        | `#163557` | `#d0ddec` | estados de feedback (sucesso, alerta, erro, info) |

O tema escuro segue `prefers-color-scheme` e pode ser forçado com `data-theme="dark"` ou `data-theme="light"` no `<html>`.

## Tipografia

| Função            | Família                   | Uso                                                                                   |
| ----------------- | ------------------------- | ------------------------------------------------------------------------------------- |
| Texto e interface | **Inter** (400, 500, 600) | corpo, listas, formulários                                                            |
| Títulos           | **Sora** (600, 700)       | `h1`–`h3`, marca                                                                      |
| Monoespaçada      | **JetBrains Mono**        | telefones, IDs, código (ainda não carregada: entra no `index.html` quando houver uso) |

Todas com fallback de sistema e `font-display: swap` (parâmetro `display=swap` do Google Fonts). Escala: `xs 12` · `sm 14` · `base 16` · `lg 18` · `xl 20` · `2xl 24` · `3xl 30` px; line-height `tight 1,25` / `normal 1,5` / `relaxed 1,625`. Pesos permitidos: 400, 500, 600, 700.

## Espaçamento, raios, sombras, z-index e animação

- Espaçamento (múltiplos de 4 px): `0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16` (× 4 px). Classes do Tailwind fora dessa escala não existem.
- Raios: `sm 4` · `md 8` · `lg 12` · `full`.
- Sombras: `sm`, `md`, `lg`.
- z-index: `base 0` · `dropdown 10` · `sticky 20` · `overlay 30` · `modal 40` · `toast 50`.
- Animação: `fast 100ms` · `base 200ms` · `slow 300ms`, easing `cubic-bezier(0.2, 0, 0, 1)`.
- Breakpoints (mobile-first): `sm 640` · `md 768` · `lg 1024` · `xl 1280` px.

## Acessibilidade (WCAG 2.2 AA)

Contraste mínimo de 4,5:1 (texto) e 3:1 (texto grande, borda de campo e anel de foco), nos dois temas. Pares verificados hoje:

| Par                                                                             | Claro   | Escuro  |
| ------------------------------------------------------------------------------- | ------- | ------- |
| texto principal na página (`text-primary` / `bg-page`)                          | 14.21:1 | 14.21:1 |
| texto principal em cartões (`text-primary` / `bg-surface`)                      | 14.70:1 | 10.11:1 |
| texto secundário na página (`text-secondary` / `bg-page`)                       | 7.04:1  | 9.20:1  |
| texto secundário em cartões (`text-secondary` / `bg-surface`)                   | 7.28:1  | 6.55:1  |
| texto discreto na página (`text-muted` / `bg-page`)                             | 4.89:1  | 7.12:1  |
| texto discreto em cartões (`text-muted` / `bg-surface`)                         | 5.05:1  | 5.07:1  |
| link na página (`text-link` / `bg-page`)                                        | 7.26:1  | 6.74:1  |
| link em cartões (`text-link` / `bg-surface`)                                    | 7.51:1  | 4.80:1  |
| texto sobre ação primária (`text-on-action` / `action-primary`)                 | 5.02:1  | 5.16:1  |
| texto sobre ação primária (hover) (`text-on-action` / `action-primary-hover`)   | 7.51:1  | 6.74:1  |
| texto sobre ação primária (active) (`text-on-action` / `action-primary-active`) | 11.39:1 | 8.60:1  |
| texto no cabeçalho (`text-on-header` / `bg-header`)                             | 5.02:1  | 11.39:1 |
| texto sobre ação secundária (`text-on-action` / `action-secondary`)             | 5.75:1  | 7.22:1  |
| selo de destaque (`accent-subtle-fg` / `accent-subtle-bg`)                      | 8.44:1  | 8.44:1  |
| selo neutro (`neutral-subtle-fg` / `neutral-subtle-bg`)                         | 8.20:1  | 5.71:1  |
| status sucesso (`status-success-fg` / `status-success-bg`)                      | 10.85:1 | 12.18:1 |
| status alerta (`status-warning-fg` / `status-warning-bg`)                       | 10.62:1 | 12.26:1 |
| status erro (`status-error-fg` / `status-error-bg`)                             | 11.24:1 | 12.13:1 |
| status info (`status-info-fg` / `status-info-bg`)                               | 11.50:1 | 12.25:1 |
| anel de foco na página (`focus-ring` / `bg-page`)                               | 4.85:1  | 6.74:1  |
| anel de foco em cartões (`focus-ring` / `bg-surface`)                           | 5.02:1  | 4.80:1  |
| borda de campos (`border-strong` / `bg-page`)                                   | 3.52:1  | 5.42:1  |
| borda de atenção (`border-attention` / `bg-page`), mínimo 3:1                   | 5.56:1  | 7.22:1  |
| indicador online (`indicator-online` / `bg-page`), mínimo 3:1                   | 5.20:1  | 6.61:1  |

Regras: foco sempre visível (`:focus-visible` global), tudo operável por teclado, `alt` em imagens, `label` em todo campo, estado nunca só por cor (o selo de status sempre traz texto).

## Componentes

- **`SuggestedTourCard`** (`src/features/suggested-tour/`): seção "Passeio sugerido pela IA" do painel da conversa. Mostra nome, descrição, selos (dificuldade em `accent-subtle`; duração e acessibilidade em `neutral-subtle`) e o preço por pessoa. Sem sugestão, mostra o texto "A IA ainda não sugeriu um passeio nesta conversa." em vez de sumir. O conteúdo vem do catálogo e é sempre texto (nunca HTML). Só usa tokens; não cria cor nova.
- **`DemoBanner`** (`src/components/`): faixa fixa (`sticky`, `z-sticky`) no topo da demonstração pública (ADR-0007), "Demonstração com dados fictícios. Nada é salvo.", com o botão de contato quando `DEMO_WHATSAPP` existe. Usa `bg-action-secondary` + `text-on-action` (mesmo par do selo "Precisa de atenção": 5,75:1 claro | 7,22:1 escuro). Só aparece no build `--mode demo`.

## Consolidação feita

- `lagoa`, `terracota`, `areia` e `grafite` viraram tokens (`primary-600`, `secondary-700`, `neutral-50`, `neutral-900`); as classes legadas foram removidas.
- Opacidades soltas (`text-grafite/60`, `opacity-70`, `bg-lagoa/10`) viraram tokens com contraste verificado: `text-muted`, `text-secondary`, `bg-accent-subtle`.
- Fontes Inter/Sora, antes duplicadas em `index.css` e no Tailwind, agora vêm de `--font-sans` / `--font-display`.
- Modo claro e escuro: o painel abre no **claro** (como o desenho), mesmo que o sistema prefira escuro, e o botão de sol/lua no topo alterna. A escolha fica em `localStorage` (`painel-tema`) e vira o atributo `data-theme` da página, que aciona os tokens escuros de `tokens.css`. Sem `data-theme`, os tokens ainda seguem `prefers-color-scheme`.
- Larguras estruturais do painel (`--size-sidebar` 14rem, `--size-panel` 20rem, `--size-search` 18rem) são tokens, usados como `w-sidebar`, `w-panel` e `w-search`. A escala de espaçamento é restrita: uma classe fora dela (ex.: `w-56`, `py-1.5`) não gera CSS e não dá erro, então o e2e confere as larguras reais.
- Redesign do painel: casca com barra lateral e topo, lista com abas de status, busca e avatar de idioma, conversa em balões com painel lateral. Só reaproveitou a paleta existente; os dois tokens novos acima apontam para cores que já estavam na paleta. Os contrastes dos selos de status estão comentados em `StatusBadge.tsx`.
- Corrigido: o texto de "transcrito de áudio" usava `opacity-70` sobre o balão enviado e perdia contraste.
