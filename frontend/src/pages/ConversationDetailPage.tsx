import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { getConversation } from "../lib/api";
import type { ConversationDetail } from "../types";

export function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<ConversationDetail | null | undefined>(
    undefined
  );

  useEffect(() => {
    if (!id) return;
    let active = true;
    getConversation(id).then((data) => {
      if (active) setConversation(data);
    });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <Link to="/" className="text-sm text-lagoa hover:underline">
        ← voltar
      </Link>

      {conversation === undefined && <p className="mt-8 text-grafite/60">Carregando…</p>}
      {conversation === null && <p className="mt-8 text-grafite/60">Conversa não encontrada.</p>}

      {conversation && (
        <>
          <div className="mt-4 flex items-center justify-between">
            <h1 className="font-display text-xl font-semibold text-grafite">
              {conversation.whatsapp_phone}
            </h1>
            <StatusBadge status={conversation.status} />
          </div>

          <ul className="mt-6 space-y-3">
            {conversation.messages.map((message) => (
              <li
                key={message.id}
                className={`max-w-md rounded-lg px-4 py-2 ${
                  message.direction === "entrada"
                    ? "bg-white border border-grafite/10"
                    : "ml-auto bg-lagoa text-white"
                }`}
              >
                <p>{message.conteudo}</p>
                {message.tipo === "audio_transcrito" && (
                  <p className="mt-1 text-xs opacity-70">transcrito de áudio</p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
