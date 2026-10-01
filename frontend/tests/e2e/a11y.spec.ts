import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { SUGGESTED_TOUR as TOUR } from "./fixtures";

/** Acessibilidade (WCAG 2.2 AA) das telas do painel, nos dois temas, com dados simulados. */
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const MESSAGE = {
  id: "a11y-m1",
  direction: "entrada",
  tipo: "texto",
  conteudo: "quero falar com um atendente",
  idioma: "pt",
  created_at: "2026-09-26T09:29:00Z",
};

const HEADER = {
  id: "a11y-conversa",
  whatsapp_phone: "5598977776666",
  status: "precisa_atencao",
  idioma_detectado: "pt",
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

async function expectNoViolations(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const summary = violations.map((violation) => ({
    rule: violation.id,
    impact: violation.impact,
    help: violation.help,
    targets: violation.nodes.map((node) => node.target.join(" ")),
  }));
  expect(summary).toEqual([]);
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
      if (theme === "dark") {
        await page.getByRole("button", { name: "Usar modo escuro" }).click();
        await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      }

      await expectNoViolations(page);
    });
  }
}
