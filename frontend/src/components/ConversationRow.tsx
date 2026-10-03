import { Link } from "react-router-dom";

import { formatPhone } from "../lib/conversations";
import { formatRelativeTime } from "../lib/time";
import type { ConversationSummary } from "../types";
import { LanguageAvatar } from "./LanguageAvatar";
import { MicIcon } from "./icons";
import { StatusBadge } from "./StatusBadge";

/** Uma linha da lista: idioma, telefone, prévia da última mensagem, há quanto tempo e status. */
export function ConversationRow({
  conversation,
  now,
}: Readonly<{
  conversation: ConversationSummary;
  now: Date;
}>) {
  const { status, ultima_mensagem: last } = conversation;
  const phoneColor = status === "resolvida" ? "text-muted" : "text-primary";
  // A borda terracota faz a prioridade aparecer na lista, não só no selo (que já traz texto).
  // A borda ocupa 3 px do padding esquerdo, para o avatar não sair do alinhamento das outras linhas.
  const attention =
    status === "precisa_atencao" ? "border-l-[3px] border-l-attention bg-page pl-[13px]" : "";

  return (
    <li>
      <Link
        to={`/conversas/${conversation.id}`}
        className={`flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 hover:bg-subtle focus-visible:-outline-offset-2 ${attention}`}
      >
        <LanguageAvatar idioma={conversation.idioma_detectado} />
        <div className="min-w-0 flex-1 basis-[12rem]">
          <p className={`flex items-center gap-2 font-semibold ${phoneColor}`}>
            <span className="whitespace-nowrap">{formatPhone(conversation.whatsapp_phone)}</span>
            {last?.tipo === "audio_transcrito" && (
              <span role="img" aria-label="áudio transcrito">
                <MicIcon />
              </span>
            )}
          </p>
          {conversation.atendimento === "humano" && (
            <p className="text-xs font-semibold text-link">
              Atendendo: {conversation.atendente_nome ?? "equipe"}
            </p>
          )}
          <p className="truncate text-sm text-muted">{last?.conteudo ?? "Sem mensagens"}</p>
        </div>
        <span className="hidden shrink-0 text-sm text-muted sm:block">
          {formatRelativeTime(last?.created_at ?? conversation.updated_at, now)}
        </span>
        {/* No celular o selo não cabe ao lado do telefone: quebra para baixo, alinhado ao texto. */}
        <span className="ml-[3.5rem] sm:ml-0">
          <StatusBadge status={status} />
        </span>
      </Link>
    </li>
  );
}
