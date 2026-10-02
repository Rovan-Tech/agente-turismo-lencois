import { useRef, useState, type Dispatch, type SetStateAction } from "react";

import {
  giveBackConversation,
  sendConversationReply,
  takeOverConversation,
  updateConversationStatus,
  type ApiResult,
} from "../../lib/api";
import { newClientMessageId } from "../../lib/handoff";
import type { ConversationDetail, ConversationHeader, ConversationStatus } from "../../types";

type SetConversation = Dispatch<SetStateAction<ConversationDetail | null | undefined>>;

export interface ConversationActions {
  /** Uma ação do painel (status, assumir, devolver) em andamento. */
  busy: boolean;
  /** A troca de status falhou. */
  statusFailed: boolean;
  /** Recusa de assumir ou devolver, na frase que o servidor mandou (ou na padrão). */
  handoffError: string | null;
  /** Recusa ou falha do envio da resposta, na frase do servidor (ou na padrão). */
  replyError: string | null;
  changeStatus: (next: ConversationStatus) => Promise<void>;
  takeOver: () => Promise<void>;
  giveBack: () => Promise<void>;
  /** Devolve `true` quando o servidor aceitou (o campo de resposta só limpa nesse caso). */
  sendReply: (text: string) => Promise<boolean>;
}

/** Ações do atendente sobre a conversa: troca de status, assumir, devolver e responder. */
export function useConversationActions(
  id: string | undefined,
  setConversation: SetConversation,
  reload: () => Promise<void>,
  callbacks: { onResolved: () => void; onTookOver: () => void; onGaveBack: () => void }
): ConversationActions {
  const [busy, setBusy] = useState(false);
  const [statusFailed, setStatusFailed] = useState(false);
  const [handoffError, setHandoffError] = useState<string | null>(null);
  const [replyError, setReplyError] = useState<string | null>(null);
  // O id do envio só muda quando o texto muda: repetir o mesmo texto depois de uma falha reaproveita
  // o id e o servidor não manda duas vezes.
  const pending = useRef<{ text: string; clientId: string } | null>(null);

  /** Aplica o cabeçalho devolvido só se a tela ainda mostra a mesma conversa. */
  function applyHeader(header: ConversationHeader) {
    setConversation((current) => (current?.id === header.id ? { ...current, ...header } : current));
  }

  /** Roda a ação, aplica o cabeçalho devolvido e diz se o servidor aceitou. */
  async function run(
    call: () => Promise<ApiResult<ConversationHeader>>,
    onFail: (message: string) => void
  ): Promise<boolean> {
    if (!id) return false;
    setBusy(true);
    const result = await call();
    setBusy(false);
    if (!result.ok) {
      onFail(result.message);
      return false;
    }
    applyHeader(result.data);
    return true;
  }

  async function changeStatus(next: ConversationStatus) {
    setStatusFailed(false);
    const accepted = await run(
      () => updateConversationStatus(id ?? "", next),
      () => setStatusFailed(true)
    );
    if (accepted && next === "resolvida") callbacks.onResolved();
  }

  /** Assumir e devolver mudam também as mensagens (o aviso ao turista), então a tela é relida. */
  async function changeHandling(
    call: () => Promise<ApiResult<ConversationHeader>>,
    onAccepted: () => void
  ) {
    setHandoffError(null);
    const accepted = await run(call, setHandoffError);
    // Recusada (ex.: outra pessoa assumiu antes) a tela também é relida, para mostrar o estado real.
    await reload();
    if (accepted) onAccepted();
  }

  async function sendReply(text: string): Promise<boolean> {
    if (!id) return false;
    if (pending.current?.text !== text) pending.current = { text, clientId: newClientMessageId() };
    setReplyError(null);
    const result = await sendConversationReply(id, text, pending.current.clientId);
    if (!result.ok) {
      setReplyError(result.message);
      return false;
    }
    pending.current = null;
    setConversation((current) =>
      current?.id === id && !current.messages.some((m) => m.id === result.data.id)
        ? { ...current, messages: [...current.messages, result.data] }
        : current
    );
    return true;
  }

  return {
    busy,
    statusFailed,
    handoffError,
    replyError,
    changeStatus,
    takeOver: () => changeHandling(() => takeOverConversation(id ?? ""), callbacks.onTookOver),
    giveBack: () => changeHandling(() => giveBackConversation(id ?? ""), callbacks.onGaveBack),
    sendReply,
  };
}
