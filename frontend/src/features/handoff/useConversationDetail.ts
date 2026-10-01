import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { getConversation } from "../../lib/api";
import { POLL_INTERVAL_MS } from "../../lib/handoff";
import type { ConversationDetail } from "../../types";

type DetailState = ConversationDetail | null | undefined;

/**
 * A conversa aberta na tela: `undefined` carregando, `null` não encontrada. Enquanto uma pessoa
 * atende ela é relida sozinha (o atendente precisa ver o que o turista escreve), sem piscar a tela
 * e só com a aba visível.
 */
export function useConversationDetail(
  id: string | undefined
): [DetailState, Dispatch<SetStateAction<DetailState>>, () => Promise<void>] {
  const [conversation, setConversation] = useState<DetailState>(undefined);

  const reload = useCallback(async () => {
    if (!id) return;
    const data = await getConversation(id);
    // Se a relida falhar, a tela mantém o que já mostra em vez de virar "não encontrada".
    setConversation((current) => (data === null && current ? current : data));
  }, [id]);

  useEffect(() => {
    let active = true;
    if (id) {
      getConversation(id).then((data) => {
        if (active) setConversation(data);
      });
    }
    return () => {
      active = false;
    };
  }, [id]);

  const isHandled = conversation?.atendimento === "humano";
  useEffect(() => {
    if (!isHandled) return;
    const timer = setInterval(() => {
      if (!document.hidden) void reload();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [isHandled, reload]);

  return [conversation, setConversation, reload];
}
