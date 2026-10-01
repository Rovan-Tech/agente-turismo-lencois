/**
 * Proxy do painel para a API (ADR-0006), executado como Pages Function em `/api/*`.
 *
 * O navegador fala só com a própria origem do painel, atrás do Cloudflare Access. O Access injeta o
 * JWT da pessoa no cabeçalho `Cf-Access-Jwt-Assertion`; o proxy o repassa ao Cloud Run, que o valida.
 * A origem do Cloud Run é fixa (variável `API_ORIGIN`): o proxy nunca é um proxy aberto.
 */

export interface ProxyEnv {
  API_ORIGIN?: string;
}

const ALLOWED_METHODS = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);

// Lista de permitidos, não de bloqueados: o cookie de sessão e qualquer outro cabeçalho não passam.
const FORWARDED_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "cf-access-jwt-assertion",
  "x-panel-request",
];

function json(status: number, detail: string, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...headers },
  });
}

/** Só caminhos de `/api/` sem truques de codificação e fora da rota do n8n (`/api/ingest`). */
function isAllowedPath(pathname: string): boolean {
  if (!pathname.startsWith("/api/")) return false;
  if (/%2e|%2f|%5c|\\|\/\//i.test(pathname)) return false;
  const lower = pathname.toLowerCase();
  return lower !== "/api/ingest" && !lower.startsWith("/api/ingest/");
}

/** A origem precisa ser exatamente `https://host`, sem caminho nem barra no fim. */
function resolveOrigin(env: ProxyEnv): string | null {
  const raw = env.API_ORIGIN;
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.protocol === "https:" && url.origin === raw ? raw : null;
  } catch {
    return null;
  }
}

export async function handleApiProxy(
  request: Request,
  env: ProxyEnv,
  fetcher: typeof fetch = fetch
): Promise<Response> {
  const url = new URL(request.url);
  if (!ALLOWED_METHODS.has(request.method)) {
    return json(405, "método não permitido", { allow: [...ALLOWED_METHODS].join(", ") });
  }
  if (!isAllowedPath(url.pathname)) return json(404, "não encontrado");
  if (request.method !== "GET" && request.headers.get("x-panel-request") !== "1") {
    return json(403, "cabeçalho do painel ausente");
  }
  const origin = resolveOrigin(env);
  if (!origin) return json(500, "proxy mal configurado");

  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }

  let upstream: Response;
  try {
    upstream = await fetcher(`${origin}${url.pathname}${url.search}`, {
      method: request.method,
      headers,
      body: request.method === "GET" ? undefined : request.body,
      redirect: "manual",
      duplex: "half",
    } as RequestInit);
  } catch {
    return json(502, "API indisponível");
  }

  const response = new Response(upstream.body, upstream);
  response.headers.delete("set-cookie");
  response.headers.set("cache-control", "no-store");
  return response;
}
