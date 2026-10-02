import { afterEach, describe, expect, it, vi } from "vitest";

/** Carrega `lib/api` de novo, porque a origem e o token são lidos do ambiente na importação. */
async function loadApi(env: Record<string, string>) {
  vi.resetModules();
  for (const [name, value] of Object.entries(env)) vi.stubEnv(name, value);
  return import("../../src/lib/api");
}

function stubFetch() {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("lib/api behind the Access proxy", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("calls the API on the same origin, with no Authorization header, when nothing is configured", async () => {
    const fetchMock = stubFetch();
    const api = await loadApi({ VITE_API_BASE_URL: "", VITE_API_TOKEN: "" });

    await api.listTours();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/tours");
    expect(fetchMock.mock.calls[0][1].headers).toBeUndefined();
  });

  it("keeps sending the bearer token while one is configured", async () => {
    const fetchMock = stubFetch();
    const api = await loadApi({
      VITE_API_BASE_URL: "https://api.exemplo.run.app",
      VITE_API_TOKEN: "token-do-painel",
    });

    await api.listTours();

    expect(fetchMock.mock.calls[0][0]).toBe("https://api.exemplo.run.app/api/tours");
    expect(fetchMock.mock.calls[0][1].headers).toEqual({ Authorization: "Bearer token-do-painel" });
  });

  it.each([
    ["deleteTour", (api: typeof import("../../src/lib/api")) => api.deleteTour("x")],
    [
      "updateConversationStatus",
      (api: typeof import("../../src/lib/api")) => api.updateConversationStatus("1", "resolvida"),
    ],
  ])("sends the panel header on a change (%s)", async (_name, change) => {
    const fetchMock = stubFetch();
    const api = await loadApi({ VITE_API_BASE_URL: "", VITE_API_TOKEN: "" });

    await change(api);

    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ "X-Panel-Request": "1" });
  });

  it("does not send the panel header on a read", async () => {
    const fetchMock = stubFetch();
    const api = await loadApi({ VITE_API_BASE_URL: "", VITE_API_TOKEN: "" });

    await api.listConversations();

    expect(fetchMock.mock.calls[0][1].headers).toBeUndefined();
  });
});
