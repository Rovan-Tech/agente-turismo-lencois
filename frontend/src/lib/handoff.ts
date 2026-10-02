import type { ConversationMessage } from "../types";

/** A Meta só aceita texto livre até 24 h depois da última mensagem do turista. */
const WINDOW_MS = 24 * 60 * 60 * 1000;

/** Teto de uma mensagem do WhatsApp (o servidor recusa mais que isso). */
export const MAX_REPLY_LENGTH = 4096;

/** De quanto em quanto tempo a conversa é relida enquanto uma pessoa atende. */
export const POLL_INTERVAL_MS = 15_000;

export const WINDOW_CLOSED_NOTICE =
  "A última mensagem do turista tem mais de 24 horas. O WhatsApp só permite responder dentro " +
  "desse prazo: espere o turista escrever de novo.";

/** Diz se ainda dá para responder: a última mensagem do turista tem menos de 24 horas. */
export function isReplyWindowOpen(messages: ConversationMessage[], now: Date): boolean {
  const times = messages
    .filter((message) => message.autor === "turista")
    .map((message) => new Date(message.created_at).getTime());
  return times.length > 0 && now.getTime() - Math.max(...times) <= WINDOW_MS;
}

/** Id de um envio: o mesmo id numa nova tentativa não manda a mensagem duas vezes. */
export function newClientMessageId(): string {
  return crypto.randomUUID();
}
