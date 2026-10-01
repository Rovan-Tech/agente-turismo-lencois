import { describe, expect, it, vi } from "vitest";

import { onRequest } from "../../functions/api/[[path]]";
import { handleApiProxy } from "../../src/lib/apiProxy";

const ORIGIN = "https://api.exemplo.run.app";
const ENV = { API_ORIGIN: ORIGIN };
const PANEL = { "x-panel-request": "1" };
const WITH_PANEL: RequestInit = { headers: PANEL };

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

/** Lê `/api/tours` com um `fetcher` próprio, para simular o que o Cloud Run devolve ou como falha. */
function runWith(fetcher: ReturnType<typeof upstream>) {
  return handleApiProxy(new Request("https://painel.exemplo.com/api/tours"), ENV, fetcher);
}

type Refusal = [name: string, url: string, init: RequestInit, status: number, env?: object];

/** Pedidos que o proxy recusa sem chegar ao Cloud Run: nome, URL, opções e o status esperado. */
const REFUSALS: Refusal[] = [
  ["an absolute url in the path", "//evil.com/api/x", WITH_PANEL, 404],
  ["a path outside /api/", "/webhook/whatsapp", WITH_PANEL, 404],
  ["dot-dot segments", "/api/../webhook/whatsapp", WITH_PANEL, 404],
  ["encoded dot-dot segments", "/api/%2e%2e/webhook/whatsapp", WITH_PANEL, 404],
  ["an encoded slash", "/api/tours%2f..%2fwebhook", WITH_PANEL, 404],
  ["an encoded slash in upper case", "/api/tours%2F..%2Fwebhook", WITH_PANEL, 404],
  ["a backslash", "/api/tours%5cwebhook", WITH_PANEL, 404],
  ["a backslash in upper case", "/api/tours%5Cwebhook", WITH_PANEL, 404],
  ["a percent-encoded letter hiding ingest", "/api/%69ngest/atendimentos", WITH_PANEL, 404],
  ["a percent-encoded capital hiding ingest", "/api/%49ngest", WITH_PANEL, 404],
  ["an empty segment", "/api//tours", WITH_PANEL, 404],
  ["the n8n ingest route", "/api/ingest/atendimentos", WITH_PANEL, 404],
  ["the n8n ingest route in other case", "/api/INGEST/atendimentos", WITH_PANEL, 404],
  ["the ingest prefix alone", "/api/ingest", WITH_PANEL, 404],
  ["the api prefix without a slash", "/api", WITH_PANEL, 404],
  ["a resource the panel does not use", "/api/health", WITH_PANEL, 404],
  ["a trailing slash", "/api/tours/", WITH_PANEL, 404],
  ["the OPTIONS method", "/api/tours", { method: "OPTIONS" }, 405],
  ["the HEAD method", "/api/tours", { method: "HEAD" }, 405],
  ...["POST", "PUT", "PATCH", "DELETE"].map((method): Refusal => [
    `a ${method} without the panel header`,
    "/api/tours/x",
    { method, body: "{}" },
    403,
  ]),
  ...["0", "true", "11", ""].map((value): Refusal => [
    `a change with the panel header set to ${JSON.stringify(value)}`,
    "/api/tours/x",
    { method: "DELETE", headers: { "x-panel-request": value } },
    403,
  ]),
  [
    "a body declared above the limit",
    "/api/tours",
    { method: "POST", body: "{}", headers: { ...PANEL, "content-length": "65537" } },
    413,
  ],
  ...[
    ["is missing", undefined],
    ["is not https", "http://api.exemplo.run.app"],
    ["has a path", "https://api.exemplo.run.app/api"],
    ["has a trailing slash", "https://api.exemplo.run.app/"],
    ["is not a url", "nao-e-url"],
  ].map(([name, origin]): Refusal => [
    `a request when the origin ${name}`,
    "/api/tours",
    {},
    500,
    { API_ORIGIN: origin },
  ]),
];

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

  it.each(["/api/me/extra", "/api/me/", "/api/ME", "/api/meu"])(
    "does not open paths that only look like /api/me (%s)",
    async (path) => {
      const { fetcher, response } = call(path);

      expect((await response).status).toBe(404);
      expect(fetcher).not.toHaveBeenCalled();
    }
  );

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

    expect([...sent(fetcher).init.headers.keys()].sort()).toEqual(["accept-language"]);
  });

  it("marks responses as no-store and drops set-cookie", async () => {
    const { response } = call("/api/conversations");

    const result = await response;

    expect(result.headers.get("cache-control")).toBe("no-store");
    expect(result.headers.get("set-cookie")).toBeNull();
    expect(await result.text()).toBe("[]");
  });

  it("drops the redirect target and the CORS headers of the origin", async () => {
    const fetcher = upstream({
      status: 307,
      headers: {
        location: "https://api.exemplo.run.app/api/tours",
        "access-control-allow-origin": "*",
        "access-control-allow-credentials": "true",
      },
    });

    const response = await runWith(fetcher);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBeNull();
    expect(
      [...response.headers.keys()].filter((name) => name.startsWith("access-control"))
    ).toEqual([]);
  });

  it.each(REFUSALS)(
    "rejects %s without calling the origin",
    async (_name, url, init, status, env) => {
      const { fetcher, response } = call(url, init, env);

      const result = await response;

      expect(result.status).toBe(status);
      expect(fetcher).not.toHaveBeenCalled();
    }
  );

  it("tells which methods are allowed when it refuses one", async () => {
    const { response } = call("/api/tours", { method: "OPTIONS" });

    expect((await response).headers.get("allow")).toBe("GET, POST, PUT, PATCH, DELETE");
  });

  it.each([
    "/api/tours",
    "/api/tours/vagas",
    "/api/tours/passeio-bugre-orla",
    "/api/conversations",
    "/api/conversations/3f2a9c1e-77b0-4d1e-9a52-0c6d5b1f8e21/status",
    "/api/conversations/3f2a9c1e-77b0-4d1e-9a52-0c6d5b1f8e21/assumir",
    "/api/conversations/3f2a9c1e-77b0-4d1e-9a52-0c6d5b1f8e21/devolver",
    "/api/conversations/3f2a9c1e-77b0-4d1e-9a52-0c6d5b1f8e21/mensagens",
    "/api/me",
  ])("forwards the panel path %s", async (path) => {
    const { fetcher, response } = call(path);

    expect((await response).status).toBe(200);
    expect(sent(fetcher).url).toBe(`${ORIGIN}${path}`);
  });

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

  it("accepts a body exactly at the limit", async () => {
    const { response } = call("/api/tours", {
      method: "POST",
      body: "{}",
      headers: { ...PANEL, "content-length": "65536" },
    });

    expect((await response).status).toBe(200);
  });

  it("answers 502 without leaking the failure when the origin is down", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED 10.0.0.7:443"));

    const response = await runWith(fetcher);

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
