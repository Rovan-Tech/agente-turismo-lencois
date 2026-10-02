import type {
  Booking,
  BookingCreateInput,
  BookingCreated,
  ConversationDetail,
  ConversationHeader,
  ConversationMessage,
  ConversationStatus,
  ConversationSummary,
  DayOccupancy,
  Me,
  Tour,
  TourCreateInput,
  TourUpdateInput,
} from "../types";
import type { ApiResult } from "../lib/api";
import { buildDemoConversations, DEMO_TOURS } from "./fixtures";
import { announcementText, FOLLOW_UP, giveBackText, WINDOW_CLOSED } from "./texts";

/**
 * Troca de `lib/api.ts` no build de demonstração (ADR-0007): mesmos nomes e mesmos contratos, mas
 * 100% em memória, sem rede e sem armazenamento no navegador. Recarregar a página volta ao começo.
 * As regras do servidor (24 h, quem atende, conversa resolvida) são repetidas aqui para a
 * demonstração se comportar como o produto.
 */

const DAY_MS = 24 * 60 * 60 * 1000;
const FOLLOW_UP_DELAY_MS = 6_000;
const NETWORK_DELAY_MS = 250;
// Mesma capacidade padrão do servidor (`server_default` da migração): a demo não edita capacidade.
const DEMO_DAILY_CAPACITY = 30;
const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

const VISITOR: Me = { sub: "visitante", nome: "Visitante" };

let conversations: ConversationDetail[] = buildDemoConversations();
let tours: Tour[] = DEMO_TOURS.map((tour) => ({ ...tour }));
let bookings: Booking[] = [];
let nextId = 1;
const answeredByTourist = new Set<string>();
const followUpTimers = new Map<string, ReturnType<typeof setTimeout>>();

/** Volta tudo ao estado inicial (usado pelos testes; na tela basta recarregar a página). */
export function resetDemo(): void {
  conversations = buildDemoConversations();
  tours = DEMO_TOURS.map((tour) => ({ ...tour }));
  bookings = [];
  nextId = 1;
  answeredByTourist.clear();
  followUpTimers.forEach((timer) => clearTimeout(timer));
  followUpTimers.clear();
}

/** O turista da demonstração só responde enquanto uma pessoa atende: sair do atendimento o cala. */
function stopFollowUp(conversationId: string): void {
  clearTimeout(followUpTimers.get(conversationId));
  followUpTimers.delete(conversationId);
  answeredByTourist.delete(conversationId);
}

/** Pequena espera, para a tela mostrar os estados de "carregando" como no produto. */
function respond<T>(value: T): Promise<T> {
  return new Promise((resolve) =>
    setTimeout(() => resolve(structuredClone(value)), NETWORK_DELAY_MS)
  );
}

function refuse(status: number, message: string): Promise<ApiResult<never>> {
  return respond({ ok: false, status, message });
}

function find(id: string): ConversationDetail | undefined {
  return conversations.find((conversation) => conversation.id === id);
}

function header(conversation: ConversationDetail): ConversationHeader {
  const { passeio_sugerido: _tour, messages: _messages, ...rest } = conversation;
  return rest;
}

function addMessage(
  conversation: ConversationDetail,
  author: ConversationMessage["autor"],
  text: string
): ConversationMessage {
  const created: ConversationMessage = {
    id: `demo-m${nextId++}`,
    direction: author === "turista" ? "entrada" : "saida",
    tipo: "texto",
    conteudo: text,
    idioma: conversation.idioma_detectado,
    autor: author,
    created_at: new Date().toISOString(),
  };
  conversation.messages.push(created);
  conversation.updated_at = created.created_at;
  return created;
}

function isWindowOpen(conversation: ConversationDetail): boolean {
  const times = conversation.messages
    .filter((m) => m.autor === "turista")
    .map((m) => new Date(m.created_at).getTime());
  return times.length > 0 && Date.now() - Math.max(...times) <= DAY_MS;
}

function clearHandling(conversation: ConversationDetail): void {
  conversation.atendimento = "ia";
  conversation.atendente_nome = null;
  conversation.atendente_sub = null;
}

export function listConversations(): Promise<ConversationSummary[] | null> {
  // Como o servidor: resolvidas por último e, dentro de cada grupo, a mais recente primeiro.
  const resolvedLast = (c: ConversationDetail) => (c.status === "resolvida" ? 1 : 0);
  const summaries = [...conversations]
    .sort((a, b) => resolvedLast(a) - resolvedLast(b) || b.updated_at.localeCompare(a.updated_at))
    .map((conversation) => {
      const last = conversation.messages.at(-1);
      return {
        ...header(conversation),
        ultima_mensagem: last
          ? {
              conteudo: last.conteudo,
              tipo: last.tipo,
              direction: last.direction,
              created_at: last.created_at,
            }
          : null,
      };
    });
  return respond(summaries);
}

export function getConversation(id: string): Promise<ConversationDetail | null> {
  const conversation = find(id);
  if (!conversation) return respond(null);
  // O passeio sugerido acompanha o catálogo: editar o passeio muda o que a conversa mostra.
  const suggested = conversation.passeio_sugerido;
  const current = suggested ? (tours.find((t) => t.id === suggested.id) ?? suggested) : null;
  return respond({ ...conversation, passeio_sugerido: current });
}

export function getMe(): Promise<Me | null> {
  return respond(VISITOR);
}

export async function updateConversationStatus(
  id: string,
  status: ConversationStatus
): Promise<ApiResult<ConversationHeader>> {
  const conversation = find(id);
  if (!conversation) return refuse(404, "conversa não encontrada");
  conversation.status = status;
  conversation.updated_at = new Date().toISOString();
  if (status === "resolvida") {
    clearHandling(conversation);
    stopFollowUp(conversation.id);
  }
  return respond({ ok: true, data: header(conversation) });
}

export async function takeOverConversation(id: string): Promise<ApiResult<ConversationHeader>> {
  const conversation = find(id);
  if (!conversation) return refuse(404, "conversa não encontrada");
  if (conversation.status === "resolvida") {
    return refuse(409, "A conversa já foi resolvida. Reabra-a para assumir.");
  }
  if (conversation.atendimento === "humano") {
    if (conversation.atendente_sub !== VISITOR.sub) {
      return refuse(
        409,
        `A conversa já está com ${conversation.atendente_nome}. Peça para devolver à IA.`
      );
    }
    return respond({ ok: true, data: header(conversation) });
  }
  if (!isWindowOpen(conversation)) return refuse(409, WINDOW_CLOSED);
  addMessage(
    conversation,
    "atendente",
    announcementText(conversation.idioma_detectado, VISITOR.nome)
  );
  conversation.atendimento = "humano";
  conversation.atendente_nome = VISITOR.nome;
  conversation.atendente_sub = VISITOR.sub;
  return respond({ ok: true, data: header(conversation) });
}

export async function giveBackConversation(id: string): Promise<ApiResult<ConversationHeader>> {
  const conversation = find(id);
  if (!conversation) return refuse(404, "conversa não encontrada");
  if (conversation.atendimento === "humano" && isWindowOpen(conversation)) {
    addMessage(conversation, "atendente", giveBackText(conversation.idioma_detectado));
  }
  clearHandling(conversation);
  stopFollowUp(conversation.id);
  return respond({ ok: true, data: header(conversation) });
}

/** O turista da demonstração responde uma vez por atendimento, para a tela mostrar a releitura. */
function scheduleTouristFollowUp(conversation: ConversationDetail): void {
  if (answeredByTourist.has(conversation.id)) return;
  answeredByTourist.add(conversation.id);
  const timer = setTimeout(() => {
    followUpTimers.delete(conversation.id);
    addMessage(
      conversation,
      "turista",
      FOLLOW_UP[conversation.idioma_detectado ?? "pt"] ?? FOLLOW_UP.pt
    );
  }, FOLLOW_UP_DELAY_MS);
  followUpTimers.set(conversation.id, timer);
}

export async function sendConversationReply(
  id: string,
  text: string,
  clientMessageId: string
): Promise<ApiResult<ConversationMessage>> {
  const conversation = find(id);
  if (!conversation) return refuse(404, "conversa não encontrada");
  const existing = conversation.messages.find((m) => m.id === `demo-${clientMessageId}`);
  if (existing) return respond({ ok: true, data: existing });
  if (conversation.status === "resolvida") return refuse(409, "A conversa já foi resolvida.");
  if (conversation.atendimento !== "humano") {
    return refuse(409, "Assuma a conversa antes de responder (a IA voltou a atender).");
  }
  if (!isWindowOpen(conversation)) return refuse(409, WINDOW_CLOSED);
  const created = addMessage(conversation, "atendente", text);
  created.id = `demo-${clientMessageId}`;
  scheduleTouristFollowUp(conversation);
  return respond({ ok: true, data: created });
}

export function listTours(includeInactive = false): Promise<Tour[] | null> {
  return respond(tours.filter((tour) => includeInactive || tour.ativo));
}

export async function createTour(payload: TourCreateInput): Promise<ApiResult<Tour>> {
  if (tours.some((tour) => tour.id === payload.id)) {
    return refuse(409, "já existe um passeio com esse id");
  }
  const created: Tour = { ...payload, ativo: payload.ativo ?? true };
  tours = [...tours, created];
  return respond({ ok: true, data: created });
}

export async function updateTour(id: string, payload: TourUpdateInput): Promise<ApiResult<Tour>> {
  const current = tours.find((tour) => tour.id === id);
  if (!current) return refuse(404, "passeio não encontrado");
  const updated: Tour = { ...payload, id };
  tours = tours.map((tour) => (tour.id === id ? updated : tour));
  return respond({ ok: true, data: updated });
}

/** Como no servidor: apagar só desativa o passeio (ele deixa de ser oferecido pela IA). */
export async function deleteTour(id: string): Promise<ApiResult<Tour>> {
  const current = tours.find((tour) => tour.id === id);
  if (!current) return refuse(404, "passeio não encontrado");
  const deactivated: Tour = { ...current, ativo: false };
  tours = tours.map((tour) => (tour.id === id ? deactivated : tour));
  return respond({ ok: true, data: deactivated });
}

function occupiedOn(tourId: string, data: string): number {
  return bookings
    .filter((booking) => booking.tour_id === tourId && booking.data === data)
    .reduce((total, booking) => total + booking.pessoas, 0);
}

/** Ocupação dia a dia do mês; passeio inativo, inexistente ou mês inválido vira `null`, como a API. */
export function getTourAgenda(tourId: string, mes: string): Promise<DayOccupancy[] | null> {
  if (!tours.some((tour) => tour.id === tourId && tour.ativo) || !MONTH_PATTERN.test(mes)) {
    return respond(null);
  }
  const [year, month] = mes.split("-").map(Number);
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return respond(
    Array.from({ length: daysInMonth }, (_, index) => {
      const data = `${mes}-${String(index + 1).padStart(2, "0")}`;
      return { data, capacidade: DEMO_DAILY_CAPACITY, ocupadas: occupiedOn(tourId, data) };
    })
  );
}

/** Lista os agendamentos pagos daquele passeio e dia; passeio inativo ou inexistente vira `null`. */
export function getDayBookings(tourId: string, data: string): Promise<Booking[] | null> {
  if (!tours.some((tour) => tour.id === tourId && tour.ativo)) return respond(null);
  return respond(bookings.filter((booking) => booking.tour_id === tourId && booking.data === data));
}

/** Como no servidor: só passeio ativo (404), sempre pago e recusa (409) o que estoura o dia. */
export async function createBooking(
  tourId: string,
  payload: BookingCreateInput
): Promise<ApiResult<BookingCreated>> {
  if (!tours.some((tour) => tour.id === tourId && tour.ativo)) {
    return refuse(404, "passeio não encontrado");
  }
  const occupied = occupiedOn(tourId, payload.data);
  if (occupied + payload.pessoas > DEMO_DAILY_CAPACITY) {
    return refuse(409, "não há vagas suficientes nesse dia");
  }
  const created: Booking = {
    ...payload,
    id: `demo-b${nextId++}`,
    tour_id: tourId,
    telefone: payload.telefone ?? null,
    status_pagamento: "pago",
    created_at: new Date().toISOString(),
  };
  bookings = [...bookings, created];
  return respond({
    ok: true,
    data: {
      ...created,
      capacidade: DEMO_DAILY_CAPACITY,
      ocupadas: occupied + payload.pessoas,
    },
  });
}
