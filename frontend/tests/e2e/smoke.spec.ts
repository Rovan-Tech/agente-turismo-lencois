import { expect, test } from "@playwright/test";

test("shows the agency header and an empty conversations list without a backend", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText("Agência de Turismo em Lençóis")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conversas no WhatsApp" })).toBeVisible();
  await expect(page.getByText("Nenhuma conversa encontrada.")).toBeVisible();
});
