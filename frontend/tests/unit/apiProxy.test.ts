import { describe, expect, it, vi } from "vitest";

import { onRequest } from "../../functions/api/[[path]]";
import { handleApiProxy } from "../../src/lib/apiProxy";

const ORIGIN = "https://api.exemplo.run.app";
const ENV = { API_ORIGIN: ORIGIN };
const PANEL = { "x-panel-request": "1" };

function upstream(init: ResponseInit = {}, body = "[]") {
  return vi.fn().mockResolvedValue(new Response(body, init));
}

function call(url: string, init: RequestInit = {}, env: { API_ORIGIN?: string } = ENV) {
  const fetcher = upstream({
    headers: { "content-type": "application/json", "set-cookie": "a=1" },
  });
  const response = handleApiProxy(
    new Request(`https://painel.exemplo.com${url}`, init),
    env,
    fetcher
  );
  return { fetcher, response };
}

/** Argumentos com que o proxy chamou o Cloud Run. */
function sent(fetcher: ReturnType<typeof upstream>) {
  const [url, init] = fetcher.mock.calls[0] as [string, RequestInit & { headers: Headers }];
  return { url, init };
}

describe("api proxy", () => {
  it("forwards a read to the fixed origin, keeping path and query", async () => {
    const { fetcher, response } = call("/api/conversations?status=aberta", {
      headers: { "cf-access-jwt-assertion": "jwt-da-pessoa", accept: "application/json" },
    });

    expect((await response).status).toBe(200);
    const { url, init } = sent(fetcher);
    expect(url).toBe(`${ORIGIN}/api/conversations?status=aberta`);
    expect(init.method).toBe("GET");
    expect(init.headers.get("cf-access-jwt-assertion")).toBe("jwt-da-pessoa");
    expect(init.redirect).toBe("manual");
  });

  it("forwards only the allowed headers, never the session cookie", async () => {
    const { fetcher, response } = call("/api/tours", {
      headers: {
        cookie: "CF_Authorization=segredo",
        authorization: "Bearer outro-token",
        "x-secret": "nao-passa",
        "accept-language": "pt-BR",
      },
    });
    await response;

    const { init } = sent(fetcher);
    expect([...init.headers.keys()].sort()).toEqual(["accept-language"]);
  });

  it("marks responses as no-store and drops set-cookie", async () => {
    const { response } = call("/api/conversations");

    const result = await response;

    expect(result.headers.get("cache-control")).toBe("no-store");
    expect(result.headers.get("set-cookie")).toBeNull();
    expect(await result.text()).toBe("[]");
  });

  it.each([
    ["an absolute url in the path", "//evil.com/api/x"],
    ["a path outside /api/", "/webhook/whatsapp"],
    ["dot-dot segments", "/api/../webhook/whatsapp"],
    ["encoded dot-dot segments", "/api/%2e%2e/webhook/whatsapp"],
    ["an encoded slash", "/api/tours%2f..%2fwebhook"],
    ["a backslash", "/api/tours%5cwebhook"],
    ["an empty segment", "/api//tours"],
    ["the n8n ingest route", "/api/ingest/atendimentos"],
    ["the n8n ingest route in other case", "/api/INGEST/atendimentos"],
    ["the ingest prefix alone", "/api/ingest"],
    ["the api prefix without a slash", "/api"],
  ])("rejects %s without calling the origin", async (_name, path) => {
    const { fetcher, response } = call(path, { headers: PANEL });

    expect((await response).status).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each(["OPTIONS", "HEAD"])("rejects the %s method", async (method) => {
    const { fetcher, response } = call("/api/tours", { method });

    const result = await response;

    expect(result.status).toBe(405);
    expect(result.headers.get("allow")).toBe("GET, POST, PUT, PATCH, DELETE");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each(["POST", "PUT", "PATCH", "DELETE"])(
    "rejects a %s without the panel header",
    async (method) => {
      const { fetcher, response } = call("/api/tours/x", { method, body: "{}" });

      expect((await response).status).toBe(403);
      expect(fetcher).not.toHaveBeenCalled();
    }
  );

  it("forwards a change with the panel header, including the body", async () => {
    const { fetcher, response } = call("/api/conversations/1/status", {
      method: "PATCH",
      body: '{"status":"resolvida"}',
      headers: { ...PANEL, "content-type": "application/json" },
    });

    expect((await response).status).toBe(200);
    const { url, init } = sent(fetcher);
    expect(url).toBe(`${ORIGIN}/api/conversations/1/status`);
    expect(init.method).toBe("PATCH");
    expect(init.headers.get("x-panel-request")).toBe("1");
    expect(await new Response(init.body as ReadableStream).text()).toBe('{"status":"resolvida"}');
  });

  it.each([
    ["is missing", undefined],
    ["is not https", "http://api.exemplo.run.app"],
    ["has a path", "https://api.exemplo.run.app/api"],
    ["has a trailing slash", "https://api.exemplo.run.app/"],
    ["is not a url", "nao-e-url"],
  ])("answers 500 when the origin %s", async (_name, origin) => {
    const { fetcher, response } = call("/api/tours", {}, { API_ORIGIN: origin });

    expect((await response).status).toBe(500);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("answers 502 without leaking the failure when the origin is down", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED 10.0.0.7:443"));

    const response = await handleApiProxy(
      new Request("https://painel.exemplo.com/api/tours"),
      ENV,
      fetcher
    );

    expect(response.status).toBe(502);
    expect(await response.text()).not.toContain("10.0.0.7");
  });

  it("is what the Pages function runs", async () => {
    vi.stubGlobal("fetch", upstream());

    const response = await onRequest({
      request: new Request("https://painel.exemplo.com/api/tours"),
      env: ENV,
    });

    expect(response.status).toBe(200);
    vi.unstubAllGlobals();
  });
});
