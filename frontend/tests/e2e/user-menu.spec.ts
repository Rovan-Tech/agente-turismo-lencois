import { expect, test } from "@playwright/test";

test("shows who is logged in and offers to sign out of the Access session", async ({ page }) => {
  await page.route("**/api/me", (route) =>
    route.fulfill({ json: { sub: "pessoa-e2e", nome: "Ana" } })
  );
  await page.route("**/api/conversations", (route) => route.fulfill({ json: [] }));

  await page.goto("/");

  await expect(page.getByText("Ana", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sair" }).first()).toHaveAttribute(
    "href",
    "/cdn-cgi/access/logout"
  );
});

test("keeps the generic name and no sign out link when nobody is logged in through Access", async ({
  page,
}) => {
  await page.route("**/api/me", (route) =>
    route.fulfill({ status: 403, json: { detail: "login" } })
  );
  await page.route("**/api/conversations", (route) => route.fulfill({ json: [] }));

  await page.goto("/");

  await expect(page.getByText("Equipe", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sair" })).toHaveCount(0);
});
