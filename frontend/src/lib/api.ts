import type { z } from "zod";

import type {
  Booking,
  BookingCreateInput,
  BookingCreated,
  ConversationDetail,
  ConversationHeader,
  ConversationStatus,
  ConversationMessage,
  ConversationSummary,
  DayOccupancy,
  Me,
  Tour,
  TourCreateInput,
  TourUpdateInput,
} from "../types";
import {
  BookingCreatedSchema,
  BookingListSchema,
  ConversationDetailSchema,
  ConversationHeaderSchema,
  ConversationListSchema,
  ConversationMessageSchema,
  DayOccupancyListSchema,
  MeSchema,
} from "./schemas";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

// Atrás do Cloudflare Access a sessão é um cookie que o navegador envia sozinho. Em toda mudança
// o painel manda este cabeçalho, que uma página de terceiro não consegue enviar (CSRF); o proxy e
// o backend o exigem.
const PANEL_HEADER = { "X-Panel-Request": "1" };

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; message: string };

/**
 * GET em JSON. Com `schema`, o corpo só chega à tela depois de validado (contrato quebrado vira
 * `null`, como qualquer outra falha). Sem `schema` é o caminho antigo, sem validação: os passeios
 * ainda o usam (dívida registrada em docs/tech-debt.md).
 */
async function fetchJson<T>(path: string, schema?: z.ZodType<T>): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : undefined,
    });
    if (!response.ok) return null;
    const body: unknown = await response.json();
    if (!schema) return body as T;
    const parsed = schema.safeParse(body);
    return parsed.success ? parsed.data : null;
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
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  body?: unknown,
  schema?: z.ZodType<T>
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...PANEL_HEADER,
        ...(API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const errorBody: unknown = await response.json().catch(() => null);
      return { ok: false, status: response.status, message: extractErrorMessage(errorBody) };
    }
    const data: unknown = await response.json();
    if (!schema) return { ok: true, data: data as T };
    const parsed = schema.safeParse(data);
    if (!parsed.success) {
      return { ok: false, status: response.status, message: "resposta inesperada do servidor" };
    }
    return { ok: true, data: parsed.data };
  } catch {
    return { ok: false, status: 0, message: "falha de conexão com o servidor" };
  }
}

export function listConversations(): Promise<ConversationSummary[] | null> {
  return fetchJson("/api/conversations", ConversationListSchema);
}

export function getConversation(id: string): Promise<ConversationDetail | null> {
  return fetchJson(`/api/conversations/${id}`, ConversationDetailSchema);
}

/** Troca o status da conversa (inclusive reabrir); o assistente o reavalia a cada mensagem. */
export function updateConversationStatus(
  id: string,
  status: ConversationStatus
): Promise<ApiResult<ConversationHeader>> {
  return sendJson(
    `/api/conversations/${encodeURIComponent(id)}/status`,
    "PATCH",
    { status },
    ConversationHeaderSchema
  );
}

/** Quem está logado (o painel mostra ao atendente o nome que o turista vai ver). */
export function getMe(): Promise<Me | null> {
  return fetchJson("/api/me", MeSchema);
}

function conversationAction(id: string, action: string): string {
  return `/api/conversations/${encodeURIComponent(id)}/${action}`;
}

/** A pessoa logada assume a conversa; o servidor avisa o turista antes de mudar o estado. */
export function takeOverConversation(id: string): Promise<ApiResult<ConversationHeader>> {
  return sendJson(conversationAction(id, "assumir"), "POST", undefined, ConversationHeaderSchema);
}

/** Devolve a conversa para a IA. */
export function giveBackConversation(id: string): Promise<ApiResult<ConversationHeader>> {
  return sendJson(conversationAction(id, "devolver"), "POST", undefined, ConversationHeaderSchema);
}

/**
 * Envia a resposta do atendente ao turista. O `clientMessageId` torna o envio idempotente: repetir
 * o mesmo id (clique duplo, nova tentativa) não manda a mensagem duas vezes.
 */
export function sendConversationReply(
  id: string,
  text: string,
  clientMessageId: string
): Promise<ApiResult<ConversationMessage>> {
  return sendJson(
    conversationAction(id, "mensagens"),
    "POST",
    { texto: text, client_message_id: clientMessageId },
    ConversationMessageSchema
  );
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

/** Ocupação dia a dia de um passeio num mês (`mes` no formato `YYYY-MM`). */
export function getTourAgenda(tourId: string, mes: string): Promise<DayOccupancy[] | null> {
  const query = `?mes=${encodeURIComponent(mes)}`;
  return fetchJson(
    `/api/tours/${encodeURIComponent(tourId)}/agenda${query}`,
    DayOccupancyListSchema
  );
}

/** Agendamentos pagos de um passeio num dia (`data` no formato `YYYY-MM-DD`). */
export function getDayBookings(tourId: string, data: string): Promise<Booking[] | null> {
  const query = `?data=${encodeURIComponent(data)}`;
  return fetchJson(
    `/api/tours/${encodeURIComponent(tourId)}/agendamentos${query}`,
    BookingListSchema
  );
}

/** Cria um agendamento — sempre entra como pago (simula "pagamento aprovado"). */
export function createBooking(
  tourId: string,
  payload: BookingCreateInput
): Promise<ApiResult<BookingCreated>> {
  return sendJson(
    `/api/tours/${encodeURIComponent(tourId)}/agendamentos`,
    "POST",
    payload,
    BookingCreatedSchema
  );
}
