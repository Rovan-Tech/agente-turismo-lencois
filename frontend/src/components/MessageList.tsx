import type { StickToBottom } from "../lib/useStickToBottom";
import type { ConversationMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

/**
 * Lista de mensagens: é a única parte da tela que rola (o cabeçalho e o campo de resposta ficam
 * parados). `tabIndex` deixa o teclado rolar a lista, e `role="log"` faz o leitor de tela anunciar
 * as mensagens novas.
 */
export function MessageList({
  messages,
  scroll,
}: Readonly<{ messages: ConversationMessage[]; scroll: StickToBottom }>) {
  return (
    <div
      ref={scroll.ref}
      onScroll={scroll.onScroll}
      role="log"
      aria-label="Mensagens da conversa"
      tabIndex={0}
      className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
    >
      <ul className="flex flex-col gap-4 px-4 py-6 sm:px-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </ul>
    </div>
  );
}
