import type {
  ConversationDetail,
  ConversationSummary,
  Tour,
  TourCreateInput,
  TourUpdateInput,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; message: string };

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : undefined,
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function extractErrorMessage(body: unknown): string {
  const fallback = "não foi possível salvar";
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return fallback;
  }
  const detail: unknown = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail) || detail.length === 0) return fallback;

  const [first]: unknown[] = detail;
  if (
    first &&
    typeof first === "object" &&
    "msg" in first &&
    typeof (first as { msg: unknown }).msg === "string"
  ) {
    return (first as { msg: string }).msg;
  }
  return fallback;
}

async function sendJson<T>(
  path: string,
  method: "POST" | "PUT" | "DELETE",
  body?: unknown
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const errorBody: unknown = await response.json().catch(() => null);
      return { ok: false, status: response.status, message: extractErrorMessage(errorBody) };
    }
    return { ok: true, data: (await response.json()) as T };
  } catch {
    return { ok: false, status: 0, message: "falha de conexão com o servidor" };
  }
}

export function listConversations(): Promise<ConversationSummary[] | null> {
  return fetchJson<ConversationSummary[]>("/api/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail | null> {
  return fetchJson<ConversationDetail>(`/api/conversations/${id}`);
}

export function listTours(includeInactive = false): Promise<Tour[] | null> {
  const query = includeInactive ? "?incluir_inativos=true" : "";
  return fetchJson<Tour[]>(`/api/tours${query}`);
}

export function createTour(payload: TourCreateInput): Promise<ApiResult<Tour>> {
  return sendJson<Tour>("/api/tours", "POST", payload);
}

export function updateTour(id: string, payload: TourUpdateInput): Promise<ApiResult<Tour>> {
  return sendJson<Tour>(`/api/tours/${encodeURIComponent(id)}`, "PUT", payload);
}

export function deleteTour(id: string): Promise<ApiResult<Tour>> {
  return sendJson<Tour>(`/api/tours/${encodeURIComponent(id)}`, "DELETE");
}
