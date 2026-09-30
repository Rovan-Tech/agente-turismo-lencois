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

## Manual V5 (itens do `docs/checklist-engenharia.md`)
- **Contratos (`FE-1`)**: toda resposta de API é validada em runtime com **Zod** em `lib/api.ts`
  (ou no `api.ts` da feature) antes de chegar ao componente; tipos vêm do schema (`z.infer`).
  ✅ `const tours = TourListSchema.parse(await res.json())` · ❌ `(await res.json()) as Tour[]`
- **Feature Slices (`FE-2`)**: funcionalidade nova em `src/features/<nome>/` com `components/`,
  `hooks/`, `api.ts`, `types.ts` e testes ao lado; o que for compartilhado sobe para `src/lib` e
  `src/components`. Uma feature não importa de outra: só de `lib/` e `components/`.
- **Segurança (`FE-3`, `FE-4`)**: nada de `dangerouslySetInnerHTML` (se inevitável, DOMPurify com
  whitelist de tags); credencial/JWT nunca em `localStorage`/`sessionStorage` (cookie HttpOnly,
  Secure, SameSite=Strict); preferência de UI (tema) pode usar `localStorage`. Sem script/estilo
  inline novo nem `unsafe-inline`/`unsafe-eval`.
- **Performance (`FE-5`)**: rota pesada com `React.lazy` + `Suspense` e skeleton; chunk ≤ 200 KB
  gzip; LCP < 2,5 s, INP < 200 ms, CLS < 0,1. Imagens com dimensões explícitas (CLS).
- **Acessibilidade e datas (`FE-6`)**: WCAG 2.2 AA no mínimo; datas chegam e saem em UTC e só a
  exibição converte para o fuso do usuário (`src/lib/time.ts`).
