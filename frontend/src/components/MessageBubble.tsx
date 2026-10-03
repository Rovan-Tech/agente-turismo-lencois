import { formatClock } from "../lib/time";
import type { ConversationMessage } from "../types";
import { MicIcon } from "./icons";

const AUTHOR_LABELS = { turista: null, ia: "Assistente de IA", atendente: "Equipe" } as const;

/** Balão da conversa: turista à esquerda, assistente à direita, com o horário embaixo. */
export function MessageBubble({ message }: Readonly<{ message: ConversationMessage }>) {
  const incoming = message.direction === "entrada";
  return (
    <li
      className={`flex max-w-[85%] flex-col gap-1 sm:max-w-xl ${incoming ? "items-start" : "ml-auto items-end"}`}
    >
      <div
        className={`rounded-lg px-4 py-2 ${
          incoming ? "border border-subtle bg-surface text-primary" : "bg-action text-on-action"
        }`}
      >
        <p>{message.conteudo}</p>
        {message.tipo === "audio_transcrito" && (
          <p className="mt-1 flex items-center gap-1 text-xs">
            <MicIcon />
            transcrito de áudio
          </p>
        )}
      </div>
      <p className="text-xs text-muted">
        {AUTHOR_LABELS[message.autor] && `${AUTHOR_LABELS[message.autor]} · `}
        <time dateTime={message.created_at}>{formatClock(message.created_at)}</time>
      </p>
    </li>
  );
}
