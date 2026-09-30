import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { listConversations } from "../lib/api";
import type { ConversationSummary } from "../types";

export function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);

  useEffect(() => {
    let active = true;
    listConversations().then((data) => {
      if (active) setConversations(data ?? []);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="font-display text-2xl font-semibold text-primary">Conversas no WhatsApp</h1>
      <p className="mt-1 text-sm text-secondary">
        Conversas com turistas atendidas pelo assistente virtual.
      </p>

      {conversations === null && <p className="mt-8 text-muted">Carregando…</p>}

      {conversations !== null && conversations.length === 0 && (
        <p className="mt-8 text-muted">Nenhuma conversa encontrada.</p>
      )}

      <ul className="mt-6 divide-y divide-subtle rounded-lg border border-subtle bg-surface">
        {conversations?.map((conversation) => (
          <li key={conversation.id}>
            <Link
              to={`/conversas/${conversation.id}`}
              className="flex items-center justify-between gap-4 px-4 py-4 hover:bg-subtle"
            >
              <div>
                <p
                  className={`font-medium ${
                    conversation.status === "resolvida" ? "text-muted" : "text-primary"
                  }`}
                >
                  {conversation.whatsapp_phone}
                </p>
                <p className="text-sm text-muted">
                  {new Date(conversation.updated_at).toLocaleString("pt-BR")}
                  {conversation.idioma_detectado ? ` · ${conversation.idioma_detectado}` : ""}
                </p>
              </div>
              <StatusBadge status={conversation.status} />
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
