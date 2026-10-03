import { expect, test } from "@playwright/test";

import { expectNoViolations, switchTheme } from "./axe";
import { bookThreePeopleWithBoleto } from "./booking";

/** A demonstração pública (ADR-0007): painel real com dados fictícios, tudo em memória. */

test("says it is a demonstration with fictional data and never calls an API", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));

  await page.goto("/");

  const note = page.getByRole("note");
  await expect(note).toContainText("Demonstração com dados fictícios. Nada é salvo.");
  await expect(note).toContainText("não uma IA ao vivo");
  await expect(note).toContainText("entre em contato com a Rovantech e solicite uma demonstração");
  await expect(page.getByText("+55 00 90000-0001")).toBeVisible();
  const own = new URL(page.url()).origin;
  const external = requests
    .filter((url) => url.startsWith("http"))
    .filter((url) => new URL(url).origin !== own)
    .filter((url) => !/^https:\/\/fonts\.(googleapis|gstatic)\.com\//.test(url));
  expect(external).toEqual([]);
  expect(requests.filter((url) => new URL(url).pathname.startsWith("/api/"))).toEqual([]);
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
  // A conversa não está em português: o atendente escreve em pt e o painel traduz antes de enviar.
  await field.fill("A busca é às 8h na pousada.");
  await page.getByRole("button", { name: "Traduzir para inglês" }).click();
  const translation =
    "This is a demo translation. In the real product, the AI translates what was typed.";
  await expect(page.getByText(translation)).toBeVisible();
  await page.getByRole("button", { name: "Enviar em inglês" }).click();
  await expect(page.getByText(translation, { exact: true })).toBeVisible();

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

  await expect(page.getByText("Lagoa Azul de 4x4").first()).toBeVisible();
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

test("lets a visitor book a tour with simulated payment, all on screen and without any API call", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(new URL(request.url()).pathname));
  await page.clock.setFixedTime(new Date("2026-09-28T09:00:00"));

  await page.goto("/passeios");
  await page.getByRole("link", { name: "Agendamentos" }).first().click();

  await expect(page.getByRole("heading", { name: "Agendamentos do passeio" })).toBeVisible();
  await expect(page.getByText("30 vagas")).toBeVisible();
  await bookThreePeopleWithBoleto(page);

  await expect(page.getByText("27 vagas")).toBeVisible();
  await expect(page.getByText("3 pessoas · Boleto")).toBeVisible();
  await expect(page.getByText("Pago")).toBeVisible();
  expect(requests.filter((path) => path.startsWith("/api/"))).toEqual([]);
});
