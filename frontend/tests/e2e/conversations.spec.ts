import { expect, test } from "@playwright/test";

const CONVERSATION = {
  id: "e2e-conversa",
  whatsapp_phone: "5598977776666",
  status: "precisa_atencao",
  idioma_detectado: "en",
  updated_at: "2026-09-26T09:30:00Z",
  messages: [
    {
      id: "e2e-m1",
      direction: "entrada",
      tipo: "texto",
      conteudo: "quero falar com um atendente",
      idioma: "en",
      created_at: "2026-09-26T09:29:00Z",
    },
  ],
};

test("marks a conversation as resolved without reloading the page", async ({ page }) => {
  let status = CONVERSATION.status;
  let statusRequests = 0;
  let detailFetches = 0;

  await page.route("**/api/conversations/e2e-conversa**", async (route) => {
    const request = route.request();
    if (request.method() === "PATCH") {
      statusRequests += 1;
      status = request.postDataJSON().status;
      await route.fulfill({ json: { ...CONVERSATION, status } });
      return;
    }
    detailFetches += 1;
    await route.fulfill({ json: { ...CONVERSATION, status } });
  });

  await page.goto("/conversas/e2e-conversa");

  await expect(page.getByRole("status")).toHaveText("Precisa de atenção");
  await expect(page.getByText("quero falar com um atendente")).toBeVisible();

  // Marcador na janela: um reload da página o apagaria.
  await page.evaluate(() => {
    (window as unknown as { semReload: boolean }).semReload = true;
  });

  await page.getByRole("button", { name: "Marcar como resolvida" }).click();

  await expect(page.getByRole("status")).toHaveText("Resolvida");
  await expect(page.getByRole("button", { name: "Marcar como resolvida" })).toHaveCount(0);
  await expect(page.getByText("quero falar com um atendente")).toBeVisible();
  expect(statusRequests).toBe(1);
  expect(detailFetches).toBe(1);
  expect(await page.evaluate(() => (window as unknown as { semReload?: boolean }).semReload)).toBe(
    true
  );
});
