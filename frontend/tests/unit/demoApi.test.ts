import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEMO_TOURS, buildDemoConversations } from "../../src/demo/fixtures";
import * as demo from "../../src/demo/demoApi";
import * as real from "../../src/lib/api";
import { ConversationDetailSchema } from "../../src/lib/schemas";

/** Espera a pequena demora simulada da "rede" e devolve o resultado. */
async function done<T>(promise: Promise<T>): Promise<T> {
  await vi.advanceTimersByTimeAsync(300);
  return promise;
}

const IN_WINDOW = "demo-c1"; // precisa de atenção, turista escreveu há minutos
const OUT_OF_WINDOW = "demo-c4"; // turista escreveu há mais de 24 h
const RESOLVED = "demo-c5";

beforeEach(() => {
  vi.useFakeTimers();
  demo.resetDemo();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("demoApi contract", () => {
  it("offers exactly the functions the real API offers, so the screens do not notice the swap", () => {
    const names = (module: object) =>
      Object.keys(module)
        .filter((k) => k !== "resetDemo")
        .sort();

    expect(names(demo)).toEqual(names(real));
  });

  it("serves conversations that follow the same schema the real API is held to", () => {
    const conversations = buildDemoConversations();

    expect(conversations.map((c) => ConversationDetailSchema.safeParse(c).success)).toEqual(
      conversations.map(() => true)
    );
  });

  it("uses only phone numbers from a range that does not exist (DDD 00), never a real one", () => {
    const phones = buildDemoConversations().map((c) => c.whatsapp_phone);

    expect(phones.every((phone) => /^5500\d{9}$/.test(phone))).toBe(true);
    expect(new Set(phones).size).toBe(phones.length);
  });

  it("never touches the network or the browser storage", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const setItem = vi.spyOn(Storage.prototype, "setItem");

    await done(demo.takeOverConversation(IN_WINDOW));
    await done(demo.sendConversationReply(IN_WINDOW, "Oi", "envio-0001"));
    await done(demo.listTours(true));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
  });
});

describe("demoApi conversations", () => {
  it("lists the newest conversations first, each with its last message as the preview", async () => {
    const list = (await done(demo.listConversations())) ?? [];

    expect(list[0].id).toBe(IN_WINDOW);
    expect(list[0].ultima_mensagem?.conteudo).toContain("talk to someone");
  });

  it("answers null for a conversation that does not exist", async () => {
    expect(await done(demo.getConversation("nao-existe"))).toBeNull();
  });

  it("says who is logged in: a visitor with a first name the tourist will see", async () => {
    expect(await done(demo.getMe())).toEqual({ sub: "visitante", nome: "Visitante" });
  });

  it("takes over, announcing the visitor to the tourist in the language of the conversation", async () => {
    const result = await done(demo.takeOverConversation(IN_WINDOW));

    expect(result).toMatchObject({
      ok: true,
      data: { atendimento: "humano", atendente_nome: "Visitante" },
    });
    const detail = await done(demo.getConversation(IN_WINDOW));
    expect(detail?.messages.at(-1)).toMatchObject({ autor: "atendente" });
    expect(detail?.messages.at(-1)?.conteudo).toContain(
      "You are now talking to a person from our team: Visitante"
    );
  });

  it.each([
    ["outside the 24 hour window", OUT_OF_WINDOW, "24 horas"],
    ["a resolved conversation", RESOLVED, "resolvida"],
  ])("refuses to take over %s, as the real server does", async (_case, id, reason) => {
    const result = await done(demo.takeOverConversation(id));

    expect(result).toMatchObject({ ok: false, status: 409 });
    expect(result.ok ? "" : result.message).toContain(reason);
  });

  it("sends a reply once per send id and keeps it in the conversation", async () => {
    await done(demo.takeOverConversation(IN_WINDOW));

    const first = await done(demo.sendConversationReply(IN_WINDOW, "Posso ajudar!", "envio-0001"));
    const again = await done(demo.sendConversationReply(IN_WINDOW, "Posso ajudar!", "envio-0001"));

    expect(first).toEqual(again);
    const detail = await done(demo.getConversation(IN_WINDOW));
    expect(detail?.messages.filter((m) => m.conteudo === "Posso ajudar!")).toHaveLength(1);
  });

  it("refuses a reply before taking over", async () => {
    expect(await done(demo.sendConversationReply(IN_WINDOW, "Oi", "envio-0001"))).toMatchObject({
      ok: false,
      status: 409,
    });
  });

  it("lets the tourist answer back once after the visitor replies, so the screen has something to reread", async () => {
    await done(demo.takeOverConversation(IN_WINDOW));
    await done(demo.sendConversationReply(IN_WINDOW, "Pick up is at 8am.", "envio-0001"));

    await vi.advanceTimersByTimeAsync(7_000);

    const detail = await done(demo.getConversation(IN_WINDOW));
    expect(detail?.messages.at(-1)).toMatchObject({ autor: "turista" });
    await done(demo.sendConversationReply(IN_WINDOW, "Great!", "envio-0002"));
    await vi.advanceTimersByTimeAsync(7_000);
    const later = await done(demo.getConversation(IN_WINDOW));
    expect(later?.messages.filter((m) => m.autor === "turista")).toHaveLength(3);
  });

  it("gives the conversation back to the AI and tells the tourist", async () => {
    await done(demo.takeOverConversation(IN_WINDOW));

    const result = await done(demo.giveBackConversation(IN_WINDOW));

    expect(result).toMatchObject({ ok: true, data: { atendimento: "ia", atendente_nome: null } });
    const detail = await done(demo.getConversation(IN_WINDOW));
    expect(detail?.messages.at(-1)?.conteudo).toContain("virtual assistant");
  });

  it("returns a resolved conversation to the AI", async () => {
    await done(demo.takeOverConversation(IN_WINDOW));

    const result = await done(demo.updateConversationStatus(IN_WINDOW, "resolvida"));

    expect(result).toMatchObject({ ok: true, data: { status: "resolvida", atendimento: "ia" } });
  });

  it("forgets everything when the demo is reset (reloading the page)", async () => {
    await done(demo.takeOverConversation(IN_WINDOW));

    demo.resetDemo();

    const detail = await done(demo.getConversation(IN_WINDOW));
    expect(detail?.atendimento).toBe("ia");
  });
});

describe("demoApi tours", () => {
  it("lists only active tours unless inactive ones are asked for", async () => {
    await done(demo.deleteTour(DEMO_TOURS[0].id));

    const active = await done(demo.listTours());
    const all = await done(demo.listTours(true));

    expect(active?.map((t) => t.id)).not.toContain(DEMO_TOURS[0].id);
    expect(all).toHaveLength(DEMO_TOURS.length);
  });

  it("creates, updates and deactivates a tour in memory, refusing a duplicate id", async () => {
    const payload = { ...DEMO_TOURS[0], id: "demo-novo", nome: "Passeio novo" };

    const created = await done(demo.createTour(payload));
    const duplicate = await done(demo.createTour(payload));
    const updated = await done(
      demo.updateTour("demo-novo", { ...payload, nome: "Outro nome", ativo: true })
    );
    const deactivated = await done(demo.deleteTour("demo-novo"));

    expect(created).toMatchObject({ ok: true, data: { id: "demo-novo", ativo: true } });
    expect(duplicate).toMatchObject({ ok: false, status: 409 });
    expect(updated).toMatchObject({ ok: true, data: { nome: "Outro nome" } });
    expect(deactivated).toMatchObject({ ok: true, data: { ativo: false } });
  });
});
