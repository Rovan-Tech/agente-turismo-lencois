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

describe("demoApi behaviour as the real server", () => {
  it("lists resolved conversations last, and a conversation just resolved moves down", async () => {
    await done(demo.updateConversationStatus(IN_WINDOW, "resolvida"));

    const list = (await done(demo.listConversations())) ?? [];

    const statuses = list.map((c) => c.status === "resolvida");
    expect(statuses).toEqual([...statuses].sort((a, b) => Number(a) - Number(b)));
    expect(list.at(-1)?.status).toBe("resolvida");
    expect(list[0].id).not.toBe(IN_WINDOW);
  });

  /** Quantas mensagens do turista a conversa tem agora. */
  async function touristMessages(id: string) {
    const detail = await done(demo.getConversation(id));
    return detail?.messages.filter((m) => m.autor === "turista").length ?? 0;
  }

  it("does not let the tourist answer when the visitor gave the conversation back first", async () => {
    const before = await touristMessages(IN_WINDOW);
    await done(demo.takeOverConversation(IN_WINDOW));
    await done(demo.sendConversationReply(IN_WINDOW, "Oi", "envio-0001"));

    await done(demo.giveBackConversation(IN_WINDOW));
    await vi.advanceTimersByTimeAsync(10_000);

    expect(await touristMessages(IN_WINDOW)).toBe(before);
  });

  it("lets the tourist answer only once after taking over again quickly", async () => {
    const before = await touristMessages(IN_WINDOW);
    await done(demo.takeOverConversation(IN_WINDOW));
    await done(demo.sendConversationReply(IN_WINDOW, "Um", "envio-0001"));
    await done(demo.giveBackConversation(IN_WINDOW));
    await done(demo.takeOverConversation(IN_WINDOW));
    await done(demo.sendConversationReply(IN_WINDOW, "Dois", "envio-0002"));

    await vi.advanceTimersByTimeAsync(10_000);

    expect(await touristMessages(IN_WINDOW)).toBe(before + 1);
  });

  it("shows the suggested tour as the catalog has it now, after the visitor edits the tour", async () => {
    const tour = DEMO_TOURS[1];
    await done(demo.updateTour(tour.id, { ...tour, preco_reais: 999 }));

    const detail = await done(demo.getConversation(IN_WINDOW));

    expect(detail?.passeio_sugerido).toMatchObject({ id: tour.id, preco_reais: 999 });
  });

  it.each([
    ["before taking over", IN_WINDOW],
    ["to a resolved conversation", RESOLVED],
  ])("refuses a reply %s", async (_when, id) => {
    expect(await done(demo.sendConversationReply(id, "Oi", "envio-0001"))).toMatchObject({
      ok: false,
      status: 409,
    });
  });

  it.each<[string, () => Promise<unknown>]>([
    ["changing the status", () => demo.updateConversationStatus("nao-existe", "aberta")],
    ["taking over", () => demo.takeOverConversation("nao-existe")],
    ["giving back", () => demo.giveBackConversation("nao-existe")],
    ["replying", () => demo.sendConversationReply("nao-existe", "Oi", "envio-0001")],
    ["updating a tour", () => demo.updateTour("nao-existe", { ...DEMO_TOURS[0] })],
    ["deactivating a tour", () => demo.deleteTour("nao-existe")],
  ])("answers 404 when %s something that does not exist", async (_what, call) => {
    expect(await done(call())).toMatchObject({ ok: false, status: 404 });
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

describe("demoApi bookings", () => {
  const TOUR = DEMO_TOURS[0].id;
  const payload = { data: "2026-10-05", pessoas: 3, forma_pagamento: "pix" as const };

  it("lists every day of the month with the daily capacity and nothing booked yet", async () => {
    const agenda = await done(demo.getTourAgenda(TOUR, "2026-02"));

    expect(agenda).toHaveLength(28);
    expect(agenda?.[0]).toEqual({ data: "2026-02-01", capacidade: 30, ocupadas: 0 });
  });

  it("returns null for an unknown tour or a malformed month, like the real API", async () => {
    expect(await done(demo.getTourAgenda("nao-existe", "2026-10"))).toBeNull();
    expect(await done(demo.getTourAgenda(TOUR, "2026-13"))).toBeNull();
    expect(await done(demo.getDayBookings("nao-existe", "2026-10-05"))).toBeNull();
  });

  it("books as paid, takes the seats off the day and lists the booking for that day only", async () => {
    const created = await done(demo.createBooking(TOUR, { ...payload, telefone: "5500900000001" }));
    const agenda = await done(demo.getTourAgenda(TOUR, "2026-10"));
    const thatDay = await done(demo.getDayBookings(TOUR, "2026-10-05"));
    const otherDay = await done(demo.getDayBookings(TOUR, "2026-10-06"));

    expect(created).toMatchObject({
      ok: true,
      data: { status_pagamento: "pago", capacidade: 30, ocupadas: 3, telefone: "5500900000001" },
    });
    expect(agenda?.find((day) => day.data === "2026-10-05")?.ocupadas).toBe(3);
    expect(thatDay).toHaveLength(1);
    expect(otherDay).toEqual([]);
  });

  it("refuses with 404 for an unknown tour and with 409 when the day would overflow", async () => {
    const unknown = await done(demo.createBooking("nao-existe", payload));
    const overflow = await done(demo.createBooking(TOUR, { ...payload, pessoas: 31 }));

    expect(unknown).toMatchObject({ ok: false, status: 404 });
    expect(overflow).toMatchObject({ ok: false, status: 409 });
  });

  it("accepts a booking that exactly fills the day, adding up across bookings, and refuses one more", async () => {
    const first = await done(demo.createBooking(TOUR, { ...payload, pessoas: 27 }));
    const second = await done(demo.createBooking(TOUR, { ...payload, pessoas: 3 }));
    const overflow = await done(demo.createBooking(TOUR, { ...payload, pessoas: 1 }));
    const agenda = await done(demo.getTourAgenda(TOUR, "2026-10"));

    expect(first).toMatchObject({ ok: true, data: { ocupadas: 27 } });
    expect(second).toMatchObject({ ok: true, data: { ocupadas: 30 } });
    expect(overflow).toMatchObject({ ok: false, status: 409 });
    expect(agenda?.find((day) => day.data === "2026-10-06")?.ocupadas).toBe(0);
  });

  it("treats a deactivated tour as gone for booking, like the server: 404 to book, read or list", async () => {
    await done(demo.deleteTour(TOUR));

    const booking = await done(demo.createBooking(TOUR, payload));
    const agenda = await done(demo.getTourAgenda(TOUR, "2026-10"));
    const dayBookings = await done(demo.getDayBookings(TOUR, "2026-10-05"));

    expect(booking).toMatchObject({ ok: false, status: 404 });
    expect(agenda).toBeNull();
    expect(dayBookings).toBeNull();
  });

  it("lists the seats of every active tour for a day, by name, and drops deactivated ones", async () => {
    await done(demo.createBooking(TOUR, payload));
    await done(demo.deleteTour(DEMO_TOURS[1].id));

    const availability = await done(demo.getTourAvailability("2026-10-05"));
    const otherDay = await done(demo.getTourAvailability("2026-10-06"));

    const activeNames = DEMO_TOURS.filter((tour) => tour.id !== DEMO_TOURS[1].id)
      .map((tour) => tour.nome)
      .sort((a, b) => a.localeCompare(b, "pt-BR"));
    expect(availability?.map((item) => item.tour_id)).toEqual(
      activeNames.map((nome) => DEMO_TOURS.find((tour) => tour.nome === nome)?.id)
    );
    expect(availability?.find((item) => item.tour_id === TOUR)).toEqual({
      tour_id: TOUR,
      capacidade: 30,
      ocupadas: 3,
    });
    expect(otherDay?.every((item) => item.ocupadas === 0)).toBe(true);
  });

  it("returns null for a malformed day, like the real API", async () => {
    expect(await done(demo.getTourAvailability("amanha"))).toBeNull();
    expect(await done(demo.getTourAvailability("2026-13-01"))).toBeNull();
  });

  it("keeps bookings and seats isolated per tour: booking one tour never touches another", async () => {
    const other = DEMO_TOURS[1].id;

    const filled = await done(demo.createBooking(TOUR, { ...payload, pessoas: 30 }));
    const otherAgenda = await done(demo.getTourAgenda(other, "2026-10"));
    const otherDayBookings = await done(demo.getDayBookings(other, "2026-10-05"));
    const otherStillBookable = await done(demo.createBooking(other, { ...payload, pessoas: 30 }));

    expect(filled).toMatchObject({ ok: true, data: { ocupadas: 30 } });
    expect(otherAgenda?.find((day) => day.data === "2026-10-05")?.ocupadas).toBe(0);
    expect(otherDayBookings).toEqual([]);
    expect(otherStillBookable).toMatchObject({ ok: true, data: { ocupadas: 30 } });
  });

  it("forgets the bookings when the demo is reset", async () => {
    await done(demo.createBooking(TOUR, payload));

    demo.resetDemo();

    expect(await done(demo.getDayBookings(TOUR, "2026-10-05"))).toEqual([]);
  });
});
