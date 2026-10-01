import { expect, test, type Page } from "@playwright/test";

const ME = { sub: "pessoa-e2e", nome: "Ana" };

function message(id: string, autor: string, text: string) {
  return {
    id,
    direction: autor === "turista" ? "entrada" : "saida",
    tipo: "texto",
    conteudo: text,
    idioma: "pt",
    autor,
    created_at: new Date().toISOString(),
  };
}

/** Simula o servidor: assumir, responder e devolver mudam o estado que as próximas leituras veem. */
async function mockHandoffApi(page: Page) {
  const state = {
    handling: "ia",
    messages: [message("m1", "turista", "quero ver o passeio de barco")],
    replies: [] as { texto: string; client_message_id: string }[],
  };
  const header = () => ({
    id: "e2e-atendimento",
    whatsapp_phone: "5598977776666",
    status: "precisa_atencao",
    idioma_detectado: "pt",
    atendimento: state.handling,
    atendente_nome: state.handling === "humano" ? ME.nome : null,
    atendente_sub: state.handling === "humano" ? ME.sub : null,
    created_at: "2026-09-20T09:00:00Z",
    updated_at: "2026-09-26T09:30:00Z",
  });
  await page.route("**/api/me", (route) => route.fulfill({ json: ME }));
  await page.route("**/api/conversations/e2e-atendimento/assumir", (route) => {
    state.handling = "humano";
    state.messages.push(message("m2", "atendente", "Agora quem está falando com você é Ana."));
    return route.fulfill({ json: header() });
  });
  await page.route("**/api/conversations/e2e-atendimento/devolver", (route) => {
    state.handling = "ia";
    return route.fulfill({ json: header() });
  });
  await page.route("**/api/conversations/e2e-atendimento/mensagens", (route) => {
    const body = route.request().postDataJSON();
    state.replies.push(body);
    const reply = message(`r${state.replies.length}`, "atendente", body.texto);
    state.messages.push(reply);
    return route.fulfill({ json: reply });
  });
  await page.route("**/api/conversations/e2e-atendimento", (route) =>
    route.fulfill({ json: { ...header(), passeio_sugerido: null, messages: state.messages } })
  );
  return state;
}

test("takes over a conversation, answers the tourist and gives it back to the AI", async ({
  page,
}) => {
  const api = await mockHandoffApi(page);

  await page.goto("/conversas/e2e-atendimento");

  await expect(page.getByText("O turista verá o aviso com o seu nome: Ana.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Resposta ao turista" })).toHaveCount(0);

  await page.getByRole("button", { name: "Assumir conversa" }).click();

  await expect(page.getByText("Você está atendendo")).toBeVisible();
  await expect(page.getByText("Agora quem está falando com você é Ana.")).toBeVisible();

  const field = page.getByRole("textbox", { name: "Resposta ao turista" });
  await field.fill("Claro! O passeio sai às 8h.");
  await page.getByRole("button", { name: "Enviar" }).click();

  await expect(page.getByText("Claro! O passeio sai às 8h.", { exact: true })).toBeVisible();
  await expect(field).toHaveValue("");
  expect(api.replies).toHaveLength(1);
  expect(api.replies[0].client_message_id).toMatch(/^[A-Za-z0-9_-]{8,64}$/);

  await page.getByRole("button", { name: "Devolver para a IA" }).click();

  await expect(page.getByRole("button", { name: "Assumir conversa" })).toBeVisible();
  await expect(field).toHaveCount(0);
});

test("lets the keyboard reach the reply field and send with Ctrl+Enter", async ({ page }) => {
  const api = await mockHandoffApi(page);
  await page.goto("/conversas/e2e-atendimento");
  await page.getByRole("button", { name: "Assumir conversa" }).click();

  const field = page.getByRole("textbox", { name: "Resposta ao turista" });
  await field.focus();
  await page.keyboard.type("Posso ajudar?");
  await page.keyboard.press("Control+Enter");

  await expect(field).toHaveValue("");
  expect(api.replies.map((reply) => reply.texto)).toEqual(["Posso ajudar?"]);
});
