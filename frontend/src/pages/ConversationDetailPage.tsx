import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { getConversation, resolveConversation } from "../lib/api";
import type { ConversationDetail } from "../types";

export function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<ConversationDetail | null | undefined>(
    undefined
  );

  const titleRef = useRef<HTMLHeadingElement>(null);
  const [resolving, setResolving] = useState(false);
  const [resolveFailed, setResolveFailed] = useState(false);

  async function handleResolve() {
    if (!id) return;
    setResolving(true);
    setResolveFailed(false);
    const result = await resolveConversation(id);
    setResolving(false);
    if (result.ok) {
      // O botão sai da tela: leva o foco ao título para o usuário de teclado não se perder.
      titleRef.current?.focus();
      // Só aplica se a tela ainda mostra a mesma conversa (resposta atrasada não vaza para outra).
      setConversation((current) =>
        current?.id === result.data.id ? { ...current, status: result.data.status } : current
      );
    } else {
      setResolveFailed(true);
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

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <Link to="/" className="text-sm text-link hover:underline">
        ← voltar
      </Link>

      {conversation === undefined && <p className="mt-8 text-muted">Carregando…</p>}
      {conversation === null && <p className="mt-8 text-muted">Conversa não encontrada.</p>}

      {conversation && (
        <>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <h1
              ref={titleRef}
              tabIndex={-1}
              className="font-display text-xl font-semibold text-primary"
            >
              {conversation.whatsapp_phone}
            </h1>
            <div className="flex items-center gap-3">
              <StatusBadge status={conversation.status} />
              {conversation.status !== "resolvida" && (
                <button
                  type="button"
                  onClick={handleResolve}
                  disabled={resolving}
                  className="rounded-md border border-subtle px-4 py-2 text-sm font-medium text-primary hover:bg-subtle active:bg-subtle disabled:bg-subtle disabled:text-muted"
                >
                  {resolving ? "Marcando…" : "Marcar como resolvida"}
                </button>
              )}
            </div>
          </div>
          {resolveFailed && (
            <p role="alert" className="mt-2 text-sm text-status-error">
              Não foi possível marcar como resolvida. Tente novamente.
            </p>
          )}

          <ul className="mt-6 space-y-3">
            {conversation.messages.map((message) => (
              <li
                key={message.id}
                className={`max-w-md rounded-lg px-4 py-2 ${
                  message.direction === "entrada"
                    ? "border border-subtle bg-surface text-primary"
                    : "ml-auto bg-action text-on-action"
                }`}
              >
                <p>{message.conteudo}</p>
                {message.tipo === "audio_transcrito" && (
                  <p className="mt-1 text-xs">transcrito de áudio</p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
