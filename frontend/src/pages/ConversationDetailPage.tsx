import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SuggestedTourCard } from "../features/suggested-tour/components/SuggestedTourCard";
import { ConversationSidePanel } from "../components/ConversationSidePanel";
import { LanguageAvatar } from "../components/LanguageAvatar";
import { MessageBubble } from "../components/MessageBubble";
import { StatusBadge } from "../components/StatusBadge";
import { ChevronLeftIcon } from "../components/icons";
import { getConversation, updateConversationStatus } from "../lib/api";
import { formatPhone, languageName } from "../lib/conversations";
import { formatCustomerSince } from "../lib/time";
import type { ConversationDetail, ConversationStatus } from "../types";

export function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<ConversationDetail | null | undefined>(
    undefined
  );
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [updating, setUpdating] = useState(false);
  const [updateFailed, setUpdateFailed] = useState(false);

  async function handleStatusChange(next: ConversationStatus) {
    if (!id) return;
    setUpdating(true);
    setUpdateFailed(false);
    const result = await updateConversationStatus(id, next);
    setUpdating(false);
    if (result.ok) {
      // O botão "Marcar como resolvida" sai da tela: leva o foco ao título para não se perder.
      if (next === "resolvida") titleRef.current?.focus();
      // Só aplica se a tela ainda mostra a mesma conversa (resposta atrasada não vaza para outra).
      setConversation((current) =>
        current?.id === result.data.id ? { ...current, status: result.data.status } : current
      );
    } else {
      setUpdateFailed(true);
    }
  }

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

  const language = conversation ? languageName(conversation.idioma_detectado) : null;

  return (
    <main className="flex flex-1 flex-col md:flex-row">
      <section className="min-w-0 flex-1">
        <Link
          to="/"
          className="flex items-center gap-1 px-4 pt-4 text-sm font-semibold text-link hover:underline sm:px-6"
        >
          <ChevronLeftIcon />
          Conversas
        </Link>

        {conversation === undefined && <p className="mt-8 px-6 text-muted">Carregando…</p>}
        {conversation === null && <p className="mt-8 px-6 text-muted">Conversa não encontrada.</p>}

        {conversation && (
          <>
            <header className="mt-3 flex flex-wrap items-center justify-between gap-3 border-b border-subtle px-4 py-4 sm:px-6">
              <div className="flex items-center gap-3">
                <LanguageAvatar idioma={conversation.idioma_detectado} />
                <div>
                  <h1
                    ref={titleRef}
                    tabIndex={-1}
                    className="font-display text-xl font-semibold text-primary"
                  >
                    {formatPhone(conversation.whatsapp_phone)}
                  </h1>
                  <p className="text-sm text-muted">
                    Cliente desde {formatCustomerSince(conversation.created_at)}
                    {language ? ` · ${language}` : ""}
                  </p>
                </div>
              </div>
              <StatusBadge status={conversation.status} />
            </header>

            <ul className="flex flex-col gap-4 px-4 py-6 sm:px-6">
              {conversation.messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </ul>
          </>
        )}
      </section>

      {conversation && (
        <ConversationSidePanel
          status={conversation.status}
          updating={updating}
          updateFailed={updateFailed}
          onChange={handleStatusChange}
        >
          <SuggestedTourCard tour={conversation.passeio_sugerido} />
        </ConversationSidePanel>
      )}
    </main>
  );
}
