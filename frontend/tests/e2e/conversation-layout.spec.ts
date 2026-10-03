import { expect, test, type Locator, type Page } from "@playwright/test";

import { expectNoViolations, switchTheme } from "./axe";

/**
 * Layout da conversa: a página tem a altura da janela e só a lista de mensagens rola (o cabeçalho
 * e o campo de resposta ficam parados), com a rolagem acompanhando as mensagens novas.
 */

const ME = { sub: "pessoa-e2e", nome: "Ana" };
const CONVERSATION_ID = "e2e-layout";
const LONG_CONVERSATION = 60;

const SIZES = [
  { width: 375, height: 667 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
] as const;
const THEMES = ["light", "dark"] as const;

let sequence = 0;

function message(autor: "turista" | "ia" | "atendente", text: string) {
  sequence += 1;
  const incoming = autor === "turista";
  return {
    autor,
    conteudo: text,
    created_at: new Date().toISOString(),
    direction: incoming ? "entrada" : "saida",
    id: `layout-m${sequence}`,
    idioma: "pt",
    tipo: "texto",
  };
}

/** Uma conversa longa e atendida por quem está logado (então o campo de resposta aparece). */
function longConversation() {
  return Array.from({ length: LONG_CONVERSATION }, (_, index) =>
    message(
      index % 2 === 0 ? "turista" : "ia",
      `Mensagem ${index + 1}: ${"texto longo da conversa ".repeat(6)}`
    )
  );
}

async function mockApi(page: Page, messages: ReturnType<typeof message>[]) {
  const header = {
    id: CONVERSATION_ID,
    whatsapp_phone: "5598977776666",
    status: "aberta",
    idioma_detectado: "pt",
    atendimento: "humano",
    atendente_nome: ME.nome,
    atendente_sub: ME.sub,
    created_at: "2026-09-20T09:00:00Z",
    updated_at: "2026-09-26T09:30:00Z",
  };
  await page.route("**/api/me", (route) => route.fulfill({ json: ME }));
  await page.route(`**/api/conversations/${CONVERSATION_ID}/mensagens`, (route) => {
    const reply = message("atendente", route.request().postDataJSON().texto);
    messages.push(reply);
    return route.fulfill({ json: reply });
  });
  await page.route(`**/api/conversations/${CONVERSATION_ID}`, (route) =>
    route.fulfill({ json: { ...header, passeio_sugerido: null, messages } })
  );
}

const messageLog = (page: Page) => page.getByRole("log", { name: "Mensagens da conversa" });
const replyField = (page: Page) => page.getByRole("textbox", { name: "Resposta ao turista" });

/** Quantos pixels faltam para o fim da lista (0 = no fim). */
const distanceFromEnd = (log: Locator) =>
  log.evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight);

/** A página inteira (não a lista) só cresceria se a conversa a esticasse. */
const pageOverflow = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);

for (const size of SIZES) {
  for (const theme of THEMES) {
    test(`long conversation scrolls only the message list at ${size.width}px in ${theme} mode`, async ({
      page,
    }) => {
      await mockApi(page, longConversation());
      await page.setViewportSize(size);
      await page.goto(`/conversas/${CONVERSATION_ID}`);
      await switchTheme(page, theme);

      const log = messageLog(page);
      const heading = page.getByRole("heading", { level: 1 });
      const lastMessage = page.getByText(`Mensagem ${LONG_CONVERSATION}:`);

      // Abre já na mensagem mais recente, com cabeçalho e campo de resposta à vista.
      await expect(lastMessage).toBeInViewport();
      await expect(heading).toBeInViewport();
      await expect(replyField(page)).toBeInViewport();
      expect(await distanceFromEnd(log)).toBeLessThanOrEqual(1);

      // A página não cresceu: a lista é que tem mais conteúdo do que cabe.
      expect(await pageOverflow(page)).toBeLessThanOrEqual(0);
      expect(await log.evaluate((el) => el.scrollHeight - el.clientHeight)).toBeGreaterThan(0);

      // Rolando a lista até o começo, o cabeçalho e o campo de resposta não saem do lugar.
      const before = await replyField(page).boundingBox();
      await log.evaluate((el) => el.scrollTo({ top: 0 }));
      await expect(page.getByText("Mensagem 1:")).toBeInViewport();
      await expect(heading).toBeInViewport();
      await expect(replyField(page)).toBeInViewport();
      expect(await replyField(page).boundingBox()).toEqual(before);
      expect(await pageOverflow(page)).toBeLessThanOrEqual(0);

      // O teclado também rola a lista (região rolável precisa de foco, WCAG 2.1.1).
      await log.focus();
      await page.keyboard.press("End");
      await expect(lastMessage).toBeInViewport();

      await expectNoViolations(page);
    });
  }
}

test.describe("scroll follows new messages only when the reader is at the end", () => {
  const POLL_MS = 15_000;
  let messages: ReturnType<typeof message>[];

  test.beforeEach(async ({ page }) => {
    // O relógio simulado adianta a releitura periódica sem esperar 15 s de verdade.
    await page.clock.install();
    messages = longConversation();
    await mockApi(page, messages);
    await page.goto(`/conversas/${CONVERSATION_ID}`);
    await expect(page.getByText(`Mensagem ${LONG_CONVERSATION}:`)).toBeInViewport();
  });

  test("follows a new message when already at the end", async ({ page }) => {
    messages.push(message("turista", "Chegou agora, no fim"));
    await page.clock.runFor(POLL_MS);

    await expect(page.getByText("Chegou agora, no fim")).toBeInViewport();
    expect(await distanceFromEnd(messageLog(page))).toBeLessThanOrEqual(1);
  });

  test("does not jump while reading older messages, and a reply brings the reader back", async ({
    page,
  }) => {
    const log = messageLog(page);
    await log.evaluate((el) => el.scrollTo({ top: 0 }));
    await expect(page.getByText("Mensagem 1:")).toBeInViewport();

    messages.push(message("turista", "Chegou enquanto eu lia"));
    await page.clock.runFor(POLL_MS);

    // A mensagem nova entrou na lista, mas a leitura ficou onde estava.
    await expect(page.getByText("Chegou enquanto eu lia")).toBeAttached();
    await expect(page.getByText("Mensagem 1:")).toBeInViewport();
    await expect(page.getByText("Chegou enquanto eu lia")).not.toBeInViewport();
    expect(await log.evaluate((el) => el.scrollTop)).toBe(0);

    // Quem responde quer ver a própria mensagem: a lista volta ao fim.
    await replyField(page).fill("Já te respondo!");
    await page.getByRole("button", { name: "Enviar" }).click();
    await expect(page.getByText("Já te respondo!", { exact: true })).toBeInViewport();
    expect(await distanceFromEnd(log)).toBeLessThanOrEqual(1);
  });
});
