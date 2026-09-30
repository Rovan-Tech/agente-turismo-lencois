import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createTour,
  deleteTour,
  getConversation,
  listConversations,
  listTours,
  updateConversationStatus,
  updateTour,
} from "../../src/lib/api";
import { SAMPLE_TOUR } from "./fixtures";

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("lib/api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("listConversations parses the JSON body on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [{ id: "1" }])));

    const result = await listConversations();

    expect(result).toEqual([{ id: "1" }]);
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
    const summary = { id: "c1", status: "aberta" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, summary));
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateConversationStatus("c1", "aberta");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/conversations/c1/status");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ status: "aberta" });
    expect(result).toEqual({ ok: true, data: summary });
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
});
