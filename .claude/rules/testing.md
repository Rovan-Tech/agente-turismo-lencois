---
paths:
  - "backend/tests/**"
  - "frontend/tests/**"
---

# Testes

Nenhuma funcionalidade está pronta sem teste, **no mesmo PR**. Bug corrigido = teste de regressão
que falhava antes da correção.

## Backend (pytest)
- Padrão Arrange-Act-Assert; nome `test_<unidade>_<cenário>_<resultado>`.
  ✅ `test_verify_signature_wrong_secret_returns_403`
- Fixtures em `conftest.py`; `@pytest.mark.parametrize` em vez de testes copiados; **sem `if`/`for`
  dentro de testes**.
- Mocks só nas fronteiras (rede, disco, relógio, Groq, WhatsApp); nunca mockar a unidade testada.
- Independentes de ordem e de estado externo. Markers: `unit`, `integration`, `e2e`.
- Todo endpoint: caminho feliz **e** de erro. Segurança: payload malicioso em `test_security.py`.
- Nada de `skip`/`xfail` novos sem issue referenciada.

## Frontend
- Vitest + Testing Library para `src/lib/` e componentes; consultas por papel/rótulo/texto.
- Não assertar classes CSS de cor além dos tokens semânticos (ex.: `bg-action-secondary`).

## E2E (Playwright, TypeScript, `frontend/tests/e2e/`)
- Toda mudança visível ou interativa no painel tem spec. A suíte sobe o próprio servidor
  (`webServer` do `playwright.config.ts`).
- Localizadores `getByRole`/`getByLabel`/`getByText`/`getByTestId`, **nunca CSS frágil**.
- Nada de `waitForTimeout`; use `expect(...)` (espera sozinho). Page Objects para fluxos repetidos.
- `trace`, `screenshot` e `video` guardados quando falhar (`retain-on-failure`).

## Cobertura
Mínimo de **90% nas linhas alteradas** (`diff-cover`); a cobertura global **nunca cai** (baseline em
`.coverage-baseline.json`).

## Manual V5 (itens do `docs/checklist-engenharia.md`)
- **Mitigação STRIDE = teste (`SEC-7`)**: cada ameaça mitigada tem teste que envia o ataque e
  confirma o bloqueio (`test_security.py`).
- **Testes que detectam defeito (`TEST-2`)**: em lógica crítica (HMAC, matcher, regras), pergunte
  "se eu quebrar esta linha, qual teste falha?". Mutação real (mutmut/Stryker) ainda não está no
  gate (TD-T1); rode manualmente na lógica crítica nova quando possível.
- **Resiliência (`OBS-3`)**: para toda integração, um teste simula timeout/5xx/queda e confirma a
  degradação graciosa. **IA (`AI-1`)**: teste com entrada adversária (injeção de prompt).
- **Acessibilidade**: componente novo tem teste por papel/rótulo e, na E2E, navegação por teclado.
