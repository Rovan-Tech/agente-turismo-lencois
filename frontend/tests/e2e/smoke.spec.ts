import { expect, test } from "@playwright/test";

test("shows the panel shell and an empty conversations list without a backend", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText("Vento Branco Expedições").first()).toBeVisible();
  await expect(page.getByText("Assistente de IA respondendo agora")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conversas", exact: true })).toBeVisible();
  await expect(page.getByText("Nenhuma conversa encontrada.")).toBeVisible();
});
