import { expect, test, type Locator, type Page } from "@playwright/test";

import { SUGGESTED_TOUR } from "./fixtures";
import { tokenColor } from "./tokens";

const TOURS = [
  { ...SUGGESTED_TOUR, id: "buggy", nome: "Passeio de Buggy", ativo: true },
  { ...SUGGESTED_TOUR, id: "barco", nome: "Passeio de Barco", ativo: true },
  { ...SUGGESTED_TOUR, id: "trilha", nome: "Trilha das Lagoas", ativo: true },
];

/** Vagas por dia: o mesmo passeio muda de nível (verde, âmbar, esgotado) conforme o dia pedido. */
const SEATS_BY_DAY: Record<string, { tour_id: string; capacidade: number; ocupadas: number }[]> = {
  "2026-09-28": [
    { tour_id: "barco", capacidade: 30, ocupadas: 26 },
    { tour_id: "buggy", capacidade: 40, ocupadas: 6 },
    { tour_id: "trilha", capacidade: 20, ocupadas: 20 },
  ],
  "2026-09-29": [
    { tour_id: "barco", capacidade: 30, ocupadas: 30 },
    { tour_id: "buggy", capacidade: 40, ocupadas: 24 },
    { tour_id: "trilha", capacidade: 20, ocupadas: 0 },
  ],
  "2026-09-30": [
    { tour_id: "barco", capacidade: 30, ocupadas: 0 },
    { tour_id: "buggy", capacidade: 40, ocupadas: 40 },
    { tour_id: "trilha", capacidade: 20, ocupadas: 12 },
  ],
};

async function mockBackend(page: Page, requestedDays: string[] = []) {
  await page.clock.setFixedTime(new Date("2026-09-28T09:00:00"));
  await page.route("**/api/tours**", (route) => route.fulfill({ json: TOURS }));
  await page.route("**/api/tours/vagas**", (route) => {
    const dia = new URL(route.request().url()).searchParams.get("dia") ?? "";
    requestedDays.push(dia);
    return route.fulfill({ json: SEATS_BY_DAY[dia] ?? [] });
  });
}

function row(page: Page, name: string): Locator {
  return page.getByRole("link", { name: new RegExp(name) });
}

test("switches the day tab and reads each tour's seats, with the three occupancy colors", async ({
  page,
}) => {
  const requestedDays: string[] = [];
  await mockBackend(page, requestedDays);

  await page.goto("/passeios");

  await expect(page.getByRole("heading", { name: "Vagas por dia" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Hoje" })).toHaveAttribute("aria-pressed", "true");

  // Hoje: 40-6 = 34 vagas (verde), 30-26 = 4 vagas (âmbar), 20-20 = esgotado (terracota).
  await expect(row(page, "Passeio de Buggy").getByText("34 vagas")).toBeVisible();
  await expect(row(page, "Passeio de Barco").getByText("4 vagas")).toBeVisible();
  await expect(row(page, "Trilha das Lagoas").getByText("Esgotado")).toBeVisible();
  expect(requestedDays).toEqual(["2026-09-28"]);

  const low = await tokenColor(page, "--color-occupancy-low-bg");
  const medium = await tokenColor(page, "--color-occupancy-medium-bg");
  const full = await tokenColor(page, "--color-occupancy-full-bg");
  await expect(row(page, "Passeio de Buggy").getByText("34 vagas")).toHaveCSS(
    "background-color",
    low
  );
  await expect(row(page, "Passeio de Barco").getByText("4 vagas")).toHaveCSS(
    "background-color",
    medium
  );
  await expect(row(page, "Trilha das Lagoas").getByText("Esgotado")).toHaveCSS(
    "background-color",
    full
  );

  // Amanhã: o barco esgota, o buggy passa de 60% (âmbar) e a trilha fica livre (verde).
  await page.getByRole("button", { name: "Amanhã", exact: true }).click();
  await expect(page.getByRole("button", { name: "Amanhã", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  await expect(row(page, "Passeio de Barco").getByText("Esgotado")).toBeVisible();
  await expect(row(page, "Passeio de Buggy").getByText("16 vagas")).toBeVisible();
  await expect(row(page, "Trilha das Lagoas").getByText("20 vagas")).toBeVisible();
  await expect(row(page, "Passeio de Barco").getByText("Esgotado")).toHaveCSS(
    "background-color",
    full
  );
  await expect(row(page, "Passeio de Buggy").getByText("16 vagas")).toHaveCSS(
    "background-color",
    medium
  );
  await expect(row(page, "Trilha das Lagoas").getByText("20 vagas")).toHaveCSS(
    "background-color",
    low
  );

  // Depois de amanhã.
  await page.getByRole("button", { name: "Depois de amanhã" }).click();
  await expect(row(page, "Passeio de Buggy").getByText("Esgotado")).toBeVisible();
  await expect(row(page, "Passeio de Barco").getByText("30 vagas")).toBeVisible();
  await expect(row(page, "Trilha das Lagoas").getByText("8 vagas")).toBeVisible();
  expect(requestedDays).toEqual(["2026-09-28", "2026-09-29", "2026-09-30"]);
});

test("each row opens the tour's detail page", async ({ page }) => {
  await mockBackend(page);
  await page.route("**/api/tours/barco/**", (route) => route.fulfill({ json: [] }));

  await page.goto("/passeios");
  await row(page, "Passeio de Barco").click();

  await expect(page).toHaveURL(/\/passeios\/barco$/);
  await expect(page.getByRole("heading", { name: "Agendamentos do passeio" })).toBeVisible();
});

test("shows an alert when the seats cannot be loaded and keeps the catalog usable", async ({
  page,
}) => {
  await mockBackend(page);
  await page.route("**/api/tours/vagas**", (route) => route.fulfill({ status: 500, json: {} }));

  await page.goto("/passeios");

  await expect(page.getByRole("alert")).toHaveText("Não foi possível carregar as vagas.");
  await expect(page.getByRole("button", { name: "Novo passeio" })).toBeVisible();
});
