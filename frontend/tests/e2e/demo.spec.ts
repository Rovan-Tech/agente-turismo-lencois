import { expect, test } from "@playwright/test";

import { expectNoViolations, switchTheme } from "./axe";

/** A demonstração pública (ADR-0007): painel real com dados fictícios, tudo em memória. */

test("says it is a demonstration with fictional data and never calls an API", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));

  await page.goto("/");

  await expect(page.getByRole("note")).toHaveText(
    /Demonstração com dados fictícios. Nada é salvo./
  );
  await expect(page.getByText("+55 00 90000-0001")).toBeVisible();
  const ownOrigin = new URL(page.url()).origin;
  const calls = requests.filter(
    (url) => url.startsWith("http") && /\/api\//.test(new URL(url).pathname)
  );
  expect(calls).toEqual([]);
  expect(requests.filter((url) => url.startsWith(ownOrigin) && url.includes("run.app"))).toEqual(
    []
  );
});

test("lets a visitor take over a conversation, answer and give it back, all on screen", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: /90000-0001/ }).click();

  await expect(page.getByText("O turista verá o aviso com o seu nome: Visitante.")).toBeVisible();
  await page.getByRole("button", { name: "Assumir conversa" }).click();

  await expect(page.getByText("Você está atendendo")).toBeVisible();
  const field = page.getByRole("textbox", { name: "Resposta ao turista" });
  await expect(field).toBeFocused();
  await field.fill("Pick up is at 8am at your hotel.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByText("Pick up is at 8am at your hotel.", { exact: true })).toBeVisible();

  // O turista da demonstração responde sozinho e a tela o relê (até 15 s de atualização).
  await expect(page.getByText(/talk it over with my group/)).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "Devolver para a IA" }).click();
  await expect(page.getByRole("button", { name: "Assumir conversa" })).toBeVisible();
});

test("starts over when the page is reloaded, because nothing is saved", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /90000-0001/ }).click();
  await page.getByRole("button", { name: "Assumir conversa" }).click();
  await expect(page.getByText("Você está atendendo")).toBeVisible();

  await page.reload();

  await expect(page.getByRole("button", { name: "Assumir conversa" })).toBeVisible();
  expect(await page.evaluate(() => window.localStorage.length + window.sessionStorage.length)).toBe(
    0
  );
});

test("explains why a conversation older than 24 hours cannot be taken over", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /90000-0004/ }).click();

  await page.getByRole("button", { name: "Assumir conversa" }).click();

  await expect(page.getByRole("alert")).toContainText("24 horas");
});

test("keeps the tour catalog editable in memory", async ({ page }) => {
  await page.goto("/passeios");

  await expect(page.getByText("Lagoa Azul de 4x4")).toBeVisible();
  await page.getByRole("button", { name: "Desativar" }).first().click();

  await expect(page.getByText("Inativo").first()).toBeVisible();
});

for (const theme of ["light", "dark"] as const) {
  test(`has no WCAG 2.2 AA violations on the demonstration in ${theme} mode`, async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("+55 00 90000-0001")).toBeVisible();
    await switchTheme(page, theme);

    await expectNoViolations(page);
  });
}
