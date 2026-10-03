import { expect, test, type Page } from "@playwright/test";

import { tokenColor } from "./tokens";

const bodyColor = (page: Page) =>
  page.evaluate(() => getComputedStyle(document.body).backgroundColor);

/** Abre o painel com os scripts atrasados: quem decide o tema antes da pintura é o <head>. */
async function openWithSlowScripts(page: Page) {
  await page.route("**/assets/*.js", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.goto("/", { waitUntil: "commit" });
  await page.waitForSelector("body", { state: "attached" });
}

// O sistema do visitante prefere escuro; o painel ainda assim abre no claro (como o desenho).
test.use({ colorScheme: "dark" });

test("opens in light mode, switches to dark and remembers the choice", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const light = await tokenColor(page, "--color-bg-page");
  expect(await bodyColor(page)).toBe(light);

  await page.getByRole("button", { name: "Usar modo escuro" }).click();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const dark = await tokenColor(page, "--color-bg-page");
  expect(dark).not.toBe(light);
  expect(await bodyColor(page)).toBe(dark);

  await page.reload();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await bodyColor(page)).toBe(dark);

  await page.getByRole("button", { name: "Usar modo claro" }).click();
  expect(await bodyColor(page)).toBe(light);
});

test("paints the right theme before the JavaScript loads (no flash)", async ({ page }) => {
  await openWithSlowScripts(page);

  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(await bodyColor(page)).toBe(await tokenColor(page, "--color-bg-page"));
});

test("paints the saved dark theme before the JavaScript loads", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("painel-tema", "dark"));
  await openWithSlowScripts(page);

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
