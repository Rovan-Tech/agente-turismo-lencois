import { expect, test, type Page } from "@playwright/test";

import { expectNoViolations, switchTheme } from "./axe";
import { HANDLING_BY_AI, SUGGESTED_TOUR as TOUR } from "./fixtures";

/** Acessibilidade (WCAG 2.2 AA) das telas do painel, nos dois temas, com dados simulados. */

const MESSAGE = {
  id: "a11y-m1",
  direction: "entrada",
  tipo: "texto",
  conteudo: "quero falar com um atendente",
  idioma: "pt",
  autor: "turista",
  created_at: "2026-09-26T09:29:00Z",
};

const HEADER = {
  id: "a11y-conversa",
  whatsapp_phone: "5598977776666",
  status: "precisa_atencao",
  idioma_detectado: "pt",
  ...HANDLING_BY_AI,
  created_at: "2026-09-20T09:00:00Z",
  updated_at: "2026-09-26T09:30:00Z",
};

/** Simula a API inteira: o scan mede a interface, não o backend. */
async function mockApi(page: Page) {
  await page.route("**/api/tours**", (route) =>
    route.fulfill({ json: [{ ...TOUR, ativo: true }] })
  );
  await page.route("**/api/conversations/a11y-conversa**", (route) =>
    route.fulfill({ json: { ...HEADER, passeio_sugerido: TOUR, messages: [MESSAGE] } })
  );
  await page.route("**/api/conversations", (route) =>
    route.fulfill({ json: [{ ...HEADER, ultima_mensagem: MESSAGE }] })
  );
}

const SCREENS: { name: string; open: (page: Page) => Promise<void> }[] = [
  {
    name: "conversations list",
    open: async (page) => {
      await page.goto("/");
      await expect(page.getByText("quero falar com um atendente")).toBeVisible();
    },
  },
  {
    name: "conversation detail",
    open: async (page) => {
      await page.goto("/conversas/a11y-conversa");
      await expect(page.getByText("Lagoa Azul de barco").first()).toBeVisible();
    },
  },
  {
    name: "conversation being attended with the reply field",
    open: async (page) => {
      const handled = {
        ...HEADER,
        atendimento: "humano",
        atendente_nome: "Ana",
        atendente_sub: "pessoa-e2e",
        passeio_sugerido: TOUR,
        messages: [{ ...MESSAGE, created_at: new Date().toISOString() }],
      };
      await page.route("**/api/me", (route) =>
        route.fulfill({ json: { sub: "pessoa-e2e", nome: "Ana" } })
      );
      await page.route("**/api/conversations/a11y-conversa**", (route) =>
        route.fulfill({ json: handled })
      );
      await page.goto("/conversas/a11y-conversa");
      await expect(page.getByRole("textbox", { name: "Resposta ao turista" })).toBeEnabled();
    },
  },
  {
    name: "tour catalog",
    open: async (page) => {
      await page.goto("/passeios");
      await expect(page.getByText("Lagoa Azul de barco").first()).toBeVisible();
    },
  },
  {
    name: "tour form",
    open: async (page) => {
      await page.goto("/passeios");
      await page.getByRole("button", { name: "Novo passeio" }).click();
      await expect(page.getByLabel("Nome")).toBeVisible();
    },
  },
];

for (const theme of ["light", "dark"] as const) {
  for (const screen of SCREENS) {
    test(`${screen.name} has no WCAG 2.2 AA violations in ${theme} mode`, async ({ page }) => {
      await mockApi(page);
      await screen.open(page);
      await switchTheme(page, theme);

      await expectNoViolations(page);
    });
  }
}
