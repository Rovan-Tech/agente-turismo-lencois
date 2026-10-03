import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/** Folga (px) para ainda contar como "no fim": o navegador arredonda a rolagem em telas com zoom. */
export const STICK_THRESHOLD_PX = 48;

export interface StickToBottom {
  /** Vai no elemento que rola (função, porque ele só existe depois que a conversa carrega). */
  ref: (element: HTMLElement | null) => void;
  onScroll: () => void;
  /** Cola no fim agora e passa a acompanhar as próximas mensagens (ex.: depois de enviar). */
  pin: () => void;
}

/**
 * Mantém uma lista rolável no fim enquanto a pessoa está no fim: abre já na mensagem mais recente
 * e acompanha as que chegam. Se ela subiu para ler as antigas, nada se mexe (a leitura não "pula").
 *
 * `resetKey` identifica a conversa aberta (trocar de conversa volta ao fim) e `changeKey` muda
 * quando chega conteúdo novo (ex.: id da última mensagem).
 */
export function useStickToBottom(
  resetKey: string | undefined,
  changeKey: string | null
): StickToBottom {
  const [element, setElement] = useState<HTMLElement | null>(null);
  const stuck = useRef(true);
  const lastReset = useRef(resetKey);
  const lastTop = useRef(0);

  const scrollToEnd = useCallback(() => {
    if (!element) return;
    element.scrollTop = element.scrollHeight;
    lastTop.current = element.scrollTop;
  }, [element]);

  // Só quem sobe a rolagem sai do fim. O navegador também mexe na posição sozinho (ajuste de
  // âncora quando o conteúdo cresce, fonte que carrega): isso nunca sobe, então não conta.
  const onScroll = useCallback(() => {
    if (!element) return;
    const top = element.scrollTop;
    const movedUp = top < lastTop.current;
    lastTop.current = top;
    const distance = element.scrollHeight - top - element.clientHeight;
    if (distance <= STICK_THRESHOLD_PX) stuck.current = true;
    else if (movedUp) stuck.current = false;
  }, [element]);

  const pin = useCallback(() => {
    stuck.current = true;
    scrollToEnd();
  }, [scrollToEnd]);

  // Antes da pintura, para a lista nunca aparecer no topo e pular depois.
  useLayoutEffect(() => {
    if (lastReset.current !== resetKey) {
      lastReset.current = resetKey;
      stuck.current = true;
    }
    if (stuck.current) scrollToEnd();
  }, [resetKey, changeKey, scrollToEnd]);

  // O espaço da lista muda sem mensagem nova (campo de resposta aparece, janela redimensiona,
  // teclado do celular abre) e o conteúdo também (a fonte carrega e o texto quebra de outro jeito):
  // quem estava no fim continua no fim.
  useEffect(() => {
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      if (stuck.current) scrollToEnd();
    });
    observer.observe(element);
    for (const child of element.children) observer.observe(child);
    return () => observer.disconnect();
  }, [element, scrollToEnd]);

  return { ref: setElement, onScroll, pin };
}
