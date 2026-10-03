import { expect, test, type Locator, type Page } from "@playwright/test";

import { HANDLING_BY_AI, SUGGESTED_TOUR } from "./fixtures";

const CONVERSATION = {
  id: "e2e-conversa",
  whatsapp_phone: "5598977776666",
  status: "precisa_atencao",
  idioma_detectado: "en",
  ...HANDLING_BY_AI,
  created_at: "2026-09-20T09:00:00Z",
  updated_at: "2026-09-26T09:30:00Z",
  passeio_sugerido: SUGGESTED_TOUR,
  messages: [
    {
      id: "e2e-m1",
      direction: "entrada",
      tipo: "texto",
      conteudo: "quero falar com um atendente",
      idioma: "en",
      autor: "turista",
      created_at: "2026-09-26T09:29:00Z",
    },
  ],
};

/** Simula a API da conversa e conta os GET (detalhe) e PATCH (status) recebidos. */
async function mockConversationApi(page: Page) {
  const state = { status: CONVERSATION.status, fetches: 0, patches: 0 };
  // A partir de `lg`, a conversa aberta divide a tela com a lista: sem isso ela bateria na rede.
  await page.route("**/api/conversations", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/conversations/e2e-conversa**", async (route) => {
    const request = route.request();
    if (request.method() === "PATCH") {
      state.patches += 1;
      state.status = request.postDataJSON().status;
    } else {
      state.fetches += 1;
    }
    await route.fulfill({ json: { ...CONVERSATION, status: state.status } });
  });
  return state;
}

test("marks a conversation as resolved without reloading the page", async ({ page }) => {
  const api = await mockConversationApi(page);

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
  expect(api.patches).toBe(1);
  expect(api.fetches).toBe(1);
  expect(await page.evaluate(() => (window as unknown as { semReload?: boolean }).semReload)).toBe(
    true
  );
});

const INBOX = [
  ["a", "5598991842201", "aberta", "pt", "Quais passeios vocês têm pra quem tem medo de altura?"],
  ["b", "5598982127743", "precisa_atencao", "en", "Is the Lagoa Azul tour wheelchair accessible?"],
  ["c", "5598977881190", "resolvida", "es", "¿Cuánto cuesta el paseo en buggy por las dunas?"],
  ["d", "5598999456087", "aberta", "pt", "Vocês têm passeio pra criança de 3 anos?"],
].map(([id, phone, status, idioma, text]) => ({
  id,
  whatsapp_phone: phone,
  status,
  idioma_detectado: idioma,
  ...HANDLING_BY_AI,
  created_at: "2026-09-20T12:00:00Z",
  updated_at: "2026-09-28T12:00:00Z",
  ultima_mensagem: {
    conteudo: text,
    tipo: "texto",
    direction: "entrada",
    created_at: "2026-09-28T12:00:00Z",
  },
}));

test("filters the inbox by status tab and searches by phone or message", async ({ page }) => {
  await page.route("**/api/conversations", (route) => route.fulfill({ json: INBOX }));

  await page.goto("/");

  await expect(page.getByRole("button", { name: "Todas 4" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Abertas 2" })).toBeVisible();
  await expect(page.getByText("+55 98 99184-2201")).toBeVisible();

  await page.getByRole("button", { name: /^Precisam de atenção/ }).click();
  await expect(page.getByText("+55 98 98212-7743")).toBeVisible();
  await expect(page.getByText("+55 98 99184-2201")).toHaveCount(0);

  await page.getByRole("button", { name: /^Todas/ }).click();
  await page.getByRole("searchbox", { name: "Buscar por telefone ou mensagem" }).fill("criança");
  await expect(page.getByText("+55 98 99945-6087")).toBeVisible();
  await expect(page.getByText("+55 98 98212-7743")).toHaveCount(0);

  const searchbox = page.getByRole("searchbox");
  await searchbox.focus();
  // O foco da busca precisa ficar visível (anel no contêiner, que vence o outline do input).
  await expect(page.locator("label", { has: searchbox })).toHaveCSS("outline-style", "solid");
  await expect(page.getByRole("complementary", { name: "Barra lateral" })).toHaveCSS(
    "width",
    "224px"
  );

  await searchbox.fill("zzz");
  await expect(page.getByText("Nenhuma conversa corresponde ao filtro ou à busca.")).toBeVisible();
});

test("resolves a conversation from the status control in the side panel", async ({ page }) => {
  await mockConversationApi(page);

  await page.goto("/conversas/e2e-conversa");

  const control = page.getByRole("group", { name: "Status da conversa" });
  const option = (name: string) => control.getByRole("button", { name, exact: true });
  await expect(option("Precisa de atenção")).toHaveAttribute("aria-pressed", "true");
  await expect(option("Precisa de atenção")).toHaveAttribute("aria-disabled", "true");
  await expect(option("Aberta")).toHaveAttribute("aria-disabled", "false");
  // Larguras estruturais vêm de tokens; se a classe deixar de gerar CSS, o painel desalinha.
  await expect(page.getByRole("complementary", { name: "Detalhes da conversa" })).toHaveCSS(
    "width",
    "320px"
  );

  await option("Resolvida").click();

  await expect(option("Resolvida")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("status")).toHaveText("Resolvida");

  // Reabrir: a troca vale para qualquer status, não só para "Resolvida".
  await option("Aberta").click();

  await expect(option("Aberta")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("status")).toHaveText("Aberta");
});

async function boxOf(locator: Locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error("elemento sem caixa na tela");
  return box;
}

test("keeps the phone and the status badge apart on a phone-sized screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.route("**/api/conversations", (route) => route.fulfill({ json: INBOX }));

  await page.goto("/");

  // Pior caso: "Precisa de atenção" é o selo mais largo e a linha ainda tem a borda de atenção.
  const row = page.getByRole("link", { name: /98212-7743/ });
  await expect(row).toBeVisible();
  // Medir antes de a fonte carregar dá larguras de outra fonte (o teste falhava de vez em quando).
  await page.evaluate(() => document.fonts.ready);
  await expect
    .poll(async () => {
      const phone = await boxOf(row.getByText("+55 98 98212-7743"));
      const badge = await boxOf(row.getByRole("status"));
      const sideBySide = phone.x + phone.width <= badge.x;
      const badgeBelow = badge.y >= phone.y + phone.height;
      return sideBySide || badgeBelow;
    })
    .toBe(true);
});

test("sizes the tourist's message bubble to its text instead of stretching it", async ({
  page,
}) => {
  await mockConversationApi(page);
  // Abaixo de `lg` a conversa ocupa a tela inteira (sem a lista do lado, que só mostra a partir
  // dali): é a largura que dá mais espaço de sobra para esta checagem de "não esticou".
  await page.setViewportSize({ width: 700, height: 800 });

  await page.goto("/conversas/e2e-conversa");

  const bubble = page.getByText("quero falar com um atendente").locator("xpath=..");
  const thread = page.locator("ul", { has: bubble });
  expect((await boxOf(bubble)).width).toBeLessThan((await boxOf(thread)).width / 2);
});

test("shows the tour the assistant suggested for the conversation", async ({ page }) => {
  await mockConversationApi(page);

  await page.goto("/conversas/e2e-conversa");

  const card = page.getByRole("region", { name: "Passeio sugerido pela IA" });
  await expect(card.getByText("Lagoa Azul de barco")).toBeVisible();
  await expect(card.getByText("Dificuldade média")).toBeVisible();
  await expect(card.getByText("2,5h")).toBeVisible();
  await expect(card.getByText("Acessível p/ idosos")).toBeVisible();
  await expect(card.getByText("Acessível p/ cadeirantes")).toHaveCount(0);
  await expect(card.getByText("R$ 180,50")).toBeVisible();
});

test("says so when the assistant suggested no tour", async ({ page }) => {
  await page.route("**/api/conversations/e2e-conversa**", (route) =>
    route.fulfill({ json: { ...CONVERSATION, passeio_sugerido: null } })
  );

  await page.goto("/conversas/e2e-conversa");

  await expect(page.getByText("A IA ainda não sugeriu um passeio nesta conversa.")).toBeVisible();
});
