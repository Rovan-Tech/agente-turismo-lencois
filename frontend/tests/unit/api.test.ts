import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createBooking,
  createTour,
  deleteTour,
  getConversation,
  getDayBookings,
  getMe,
  getTourAgenda,
  giveBackConversation,
  listConversations,
  listTours,
  sendConversationReply,
  takeOverConversation,
  updateConversationStatus,
  updateTour,
} from "../../src/lib/api";
import {
  SAMPLE_BOOKING,
  SAMPLE_CONVERSATION,
  SAMPLE_DAY_OCCUPANCY,
  SAMPLE_SUGGESTED_TOUR,
  SAMPLE_TOUR,
  summary,
} from "./fixtures";

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

/** Faz o próximo `fetch` devolver `body` com status 200. */
function respondWith(body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, body)));
}

describe("lib/api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const loadDetail = () => getConversation("abc123");
  const [firstMessage] = SAMPLE_CONVERSATION.messages;
  const withTour = (tour: unknown) => ({ ...SAMPLE_CONVERSATION, passeio_sugerido: tour });

  it.each([
    ["a conversation list", listConversations, [summary({ id: "1" })]],
    [
      "a conversation with no messages and no detected language",
      listConversations,
      [summary({ ultima_mensagem: null, idioma_detectado: null })],
    ],
    [
      "a detail with no suggested tour and a message without language",
      loadDetail,
      { ...SAMPLE_CONVERSATION, messages: [{ ...firstMessage, idioma: null }] },
    ],
    ["a detail with the suggested tour", loadDetail, withTour(SAMPLE_SUGGESTED_TOUR)],
  ])("accepts %s that follows the contract", async (_case, load, body) => {
    respondWith(body);

    expect(await load()).toEqual(body);
  });

  it("keeps the customer name the server sends", async () => {
    respondWith([summary({ id: "1", cliente_nome: "Mariana Souza" })]);

    expect(await listConversations()).toMatchObject([{ cliente_nome: "Mariana Souza" }]);
  });

  it("treats a response without the customer name (older backend) as having no name", async () => {
    const { cliente_nome: _omitted, ...withoutName } = summary({ id: "1" });
    const { cliente_nome: _omittedToo, ...detailWithoutName } = SAMPLE_CONVERSATION;
    void [_omitted, _omittedToo];

    respondWith([withoutName]);
    expect(await listConversations()).toMatchObject([{ cliente_nome: null }]);
    respondWith(detailWithoutName);
    expect(await loadDetail()).toMatchObject({ cliente_nome: null });
  });

  it.each(["baixa", "media", "alta"] as const)(
    "accepts a suggested tour with %s difficulty",
    async (level) => {
      const detail = withTour({ ...SAMPLE_SUGGESTED_TOUR, dificuldade_fisica: level });
      respondWith(detail);

      expect(await loadDetail()).toEqual(detail);
    }
  );

  it.each([
    ["a list item missing required fields", listConversations, [{ id: "1" }]],
    [
      "a suggested tour with a field of the wrong type",
      loadDetail,
      withTour({ ...SAMPLE_SUGGESTED_TOUR, preco_reais: "barato" }),
    ],
    [
      "a suggested tour with an unknown difficulty",
      loadDetail,
      withTour({ ...SAMPLE_SUGGESTED_TOUR, dificuldade_fisica: "extrema" }),
    ],
    ["a suggested tour that is not an object", loadDetail, withTour("trilha-das-emendas")],
    ["a status that is not a known one", loadDetail, { ...withTour(null), status: "arquivada" }],
  ])("returns null for %s", async (_case, load, body) => {
    respondWith(body);

    expect(await load()).toBeNull();
  });

  it("listConversations returns null when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(500, {})));

    expect(await listConversations()).toBeNull();
  });

  it("getConversation returns null when the network call throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    expect(await getConversation("abc")).toBeNull();
  });

  it("listTours requests incluir_inativos when includeInactive is true", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal("fetch", fetchMock);

    await listTours(true);

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours?incluir_inativos=true");
  });

  it("createTour sends a POST with the payload and returns the created tour", async () => {
    const createdTour = { id: "t1", nome: "Tour" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, createdTour));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createTour(SAMPLE_TOUR);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(SAMPLE_TOUR);
    expect(result).toEqual({ ok: true, data: createdTour });
  });

  it.each([
    [409, { detail: "já existe um passeio com esse id" }, "já existe um passeio com esse id"],
    [422, { detail: [{ msg: "preco_reais deve ser positivo" }] }, "preco_reais deve ser positivo"],
  ])(
    "createTour surfaces the API error detail for a %i response",
    async (status, body, message) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(status, body)));

      const result = await createTour(SAMPLE_TOUR);

      expect(result).toEqual({ ok: false, status, message });
    }
  );

  it("updateTour sends a PUT to the tour's id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { id: "t1" }));
    vi.stubGlobal("fetch", fetchMock);

    await updateTour("t1", SAMPLE_TOUR);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours/t1");
    expect(init.method).toBe("PUT");
  });

  it("deleteTour sends a DELETE to the tour's id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { id: "t1", ativo: false }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await deleteTour("t1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours/t1");
    expect(init.method).toBe("DELETE");
    expect(result).toEqual({ ok: true, data: { id: "t1", ativo: false } });
  });

  it("deleteTour reports a connection failure when the network call throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const result = await deleteTour("t1");

    expect(result).toEqual({
      ok: false,
      status: 0,
      message: "falha de conexão com o servidor",
    });
  });

  it("updateConversationStatus sends a PATCH with the chosen status and returns the summary", async () => {
    const header = summary({ id: "c1", status: "aberta" });
    const { ultima_mensagem: _preview, ...updated } = header;
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, updated));
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateConversationStatus("c1", "aberta");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/conversations/c1/status");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ status: "aberta" });
    expect(result).toEqual({ ok: true, data: updated });
  });

  it("updateConversationStatus reports the HTTP status when the API rejects the change", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: "conversa não encontrada" }))
    );

    expect(await updateConversationStatus("x", "resolvida")).toEqual({
      ok: false,
      status: 404,
      message: "conversa não encontrada",
    });
  });

  it("updateConversationStatus reports an unexpected body instead of trusting it", async () => {
    respondWith({ id: "c1", status: 7 });

    expect(await updateConversationStatus("c1", "aberta")).toEqual({
      ok: false,
      status: 200,
      message: "resposta inesperada do servidor",
    });
  });

  it("getTourAgenda requests the given month and returns the day-by-day occupancy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [SAMPLE_DAY_OCCUPANCY]));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getTourAgenda("passeio-bugre-orla", "2026-09");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours/passeio-bugre-orla/agenda?mes=2026-09");
    expect(result).toEqual([SAMPLE_DAY_OCCUPANCY]);
  });

  it("getTourAgenda returns null for a malformed day", async () => {
    respondWith([{ ...SAMPLE_DAY_OCCUPANCY, capacidade: "muitas" }]);

    expect(await getTourAgenda("passeio-bugre-orla", "2026-09")).toBeNull();
  });

  it("getDayBookings requests the given date and returns that day's paid bookings", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [SAMPLE_BOOKING]));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getDayBookings("passeio-bugre-orla", "2026-09-28");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours/passeio-bugre-orla/agendamentos?data=2026-09-28");
    expect(result).toEqual([SAMPLE_BOOKING]);
  });

  it("getDayBookings returns null for a booking with an unknown payment method", async () => {
    respondWith([{ ...SAMPLE_BOOKING, forma_pagamento: "dinheiro" }]);

    expect(await getDayBookings("passeio-bugre-orla", "2026-09-28")).toBeNull();
  });

  it("createBooking sends a POST with the payload and returns the created booking", async () => {
    const created = { ...SAMPLE_BOOKING, capacidade: 41, ocupadas: 13 };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, created));
    vi.stubGlobal("fetch", fetchMock);
    const payload = { data: "2026-09-28", pessoas: 3, forma_pagamento: "pix" as const };

    const result = await createBooking("passeio-bugre-orla", payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/tours/passeio-bugre-orla/agendamentos");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(payload);
    expect(init.headers["X-Panel-Request"]).toBe("1");
    expect(result).toEqual({ ok: true, data: created });
  });

  it("createBooking surfaces the API error when there are not enough seats", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: "não há vagas suficientes nesse dia" }))
    );

    const result = await createBooking("passeio-bugre-orla", {
      data: "2026-09-28",
      pessoas: 50,
      forma_pagamento: "pix",
    });

    expect(result).toEqual({
      ok: false,
      status: 409,
      message: "não há vagas suficientes nesse dia",
    });
  });

  it.each([
    ["takeOverConversation", takeOverConversation, "assumir"],
    ["giveBackConversation", giveBackConversation, "devolver"],
  ])("%s sends a POST without a body, with the panel header", async (_name, act, action) => {
    const { ultima_mensagem: _preview, ...updated } = summary({ id: "c1", atendimento: "humano" });
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, updated));
    vi.stubGlobal("fetch", fetchMock);

    const result = await act("c1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain(`/api/conversations/c1/${action}`);
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(init.headers["X-Panel-Request"]).toBe("1");
    expect(result).toEqual({ ok: true, data: updated });
  });

  it("sendConversationReply posts the text and the client id, never a phone number", async () => {
    const [saved] = SAMPLE_CONVERSATION.messages;
    const sentMessage = { ...saved, id: "m9", direction: "saida", autor: "atendente" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, sentMessage));
    vi.stubGlobal("fetch", fetchMock);

    const result = await sendConversationReply("c1", "Olá!", "envio-0001");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/conversations/c1/mensagens");
    expect(JSON.parse(init.body)).toEqual({ texto: "Olá!", client_message_id: "envio-0001" });
    expect(result).toEqual({ ok: true, data: sentMessage });
  });

  it("sendConversationReply gives the server's reason when it refuses", async () => {
    const reason = "A última mensagem do turista tem mais de 24 horas.";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(409, { detail: reason })));

    expect(await sendConversationReply("c1", "Oi", "envio-0001")).toEqual({
      ok: false,
      status: 409,
      message: reason,
    });
  });

  it("getMe returns the person who is logged in, or null for an unexpected body", async () => {
    respondWith({ sub: "pessoa-123", nome: "Ana" });
    expect(await getMe()).toEqual({ sub: "pessoa-123", nome: "Ana" });

    respondWith({ sub: 123 });
    expect(await getMe()).toBeNull();
  });

  it("rejects a conversation that does not say who is answering", async () => {
    const { atendimento: _handling, ...incomplete } = SAMPLE_CONVERSATION;
    respondWith(incomplete);

    expect(await getConversation("abc123")).toBeNull();
  });
});
