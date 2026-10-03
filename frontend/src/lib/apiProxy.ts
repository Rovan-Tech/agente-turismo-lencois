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

// Teto do corpo declarado: as mudanças do painel são minúsculas (o backend também limita).
const MAX_BODY_BYTES = 64 * 1024;

// Lista de permitidos: só os recursos que o painel usa, com segmentos simples (letras, números,
// `_` e `-`). Sem `%`, `.` nem barra no fim, não há codificação, dot-segment ou caminho oculto
// (como `%69ngest`) a conferir, e a rota do n8n (`/api/ingest`) fica de fora por construção.
const PANEL_PATH = /^\/api\/(?:(?:tours|conversations)(?:\/[A-Za-z0-9_-]+)*|me)$/;

function isAllowedPath(pathname: string): boolean {
  return PANEL_PATH.test(pathname);
}

/** Corpo declarado acima do teto; sem `Content-Length` a plataforma e o backend é que limitam. */
function isBodyTooLarge(request: Request): boolean {
  const declared = Number(request.headers.get("content-length") ?? 0);
  return Number.isFinite(declared) && declared > MAX_BODY_BYTES;
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
  if (isBodyTooLarge(request)) return json(413, "corpo grande demais");
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
  // Nada do que identifica o Cloud Run volta ao navegador: cookie, destino de redirecionamento
  // (apontaria direto para o `run.app`) e cabeçalhos CORS do backend.
  // Lista antes de apagar: remover durante a iteração de `Headers` pula entradas.
  const sensitive = [...response.headers.keys()].filter(
    (name) => name === "set-cookie" || name === "location" || name.startsWith("access-control-")
  );
  for (const name of sensitive) {
    response.headers.delete(name);
  }
  response.headers.set("cache-control", "no-store");
  return response;
}
