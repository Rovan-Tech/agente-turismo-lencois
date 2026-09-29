---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# TypeScript / React

Ferramentas: `tsc --noEmit` (`strict: true`), Prettier (linha de 100), Vitest, Playwright.

- Tipagem estrita: sem `any` (use `unknown` + refinamento); `// @ts-expect-error` só com o porquê;
  nunca `@ts-ignore`. ✅ `catch (e: unknown)` · ❌ `catch (e: any)`
- Componentes de função com props tipadas; um componente por arquivo em `src/components/`.
  Componentes e páginas só **orquestram**; lógica vai para `src/lib/` ou hooks.
- Efeitos com cleanup (padrão `let active = true` já usado nas páginas) para evitar setState após
  desmontar.
- Nada de `dangerouslySetInnerHTML` com dado externo (XSS). Telefone e conteúdo de conversa são
  dado pessoal (LGPD): não vão para `console.*`.
- Estados de todo componente de dados: carregando, vazio, erro e sucesso.
- Comentários e JSDoc em pt-BR explicam o **porquê**; nomes de código em inglês.
- Estilo: só tokens do design system (ver `design-system.md`); sem `style={{ color: ... }}`.
- Tamanho e aninhamento: não há medição automática no TypeScript; o `code-reviewer` avalia
  legibilidade (componentes curtos, sem JSX aninhado em excesso). Duplicação: `jscpd` no gate.
