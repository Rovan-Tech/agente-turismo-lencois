import { useEffect, useState } from "react";

import { ConversationRow } from "../components/ConversationRow";
import { LanguageFilterTabs } from "../components/LanguageFilterTabs";
import { SearchBox } from "../components/SearchBox";
import { StatusFilterTabs } from "../components/StatusFilterTabs";
import {
  countByFilter,
  filterConversations,
  languageFilterOptions,
  type LanguageFilter,
  type StatusFilter,
} from "../lib/conversations";
import { listConversations } from "../lib/api";
import type { ConversationSummary } from "../types";

export function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("todas");
  const [language, setLanguage] = useState<LanguageFilter>("todos");
  const [query, setQuery] = useState("");
  const [now] = useState(() => new Date());

  useEffect(() => {
    let active = true;
    listConversations().then((data) => {
      if (active) setConversations(data ?? []);
    });
    return () => {
      active = false;
    };
  }, []);

  const visible = conversations ? filterConversations(conversations, filter, query, language) : [];
  const languageOptions = conversations ? languageFilterOptions(conversations) : [];

  return (
    <div className="w-full flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:overflow-y-auto">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-primary">Conversas</h1>
          <p className="mt-1 text-sm text-secondary">
            Conversas com turistas atendidas pelo assistente virtual no WhatsApp.
          </p>
        </div>
        <SearchBox value={query} onChange={setQuery} />
      </div>

      {conversations === null && <p className="mt-8 text-muted">Carregando…</p>}

      {conversations !== null && conversations.length === 0 && (
        <p className="mt-8 text-muted">Nenhuma conversa encontrada.</p>
      )}

      {conversations !== null && conversations.length > 0 && (
        <>
          <div className="mt-6 flex flex-col gap-3">
            <StatusFilterTabs
              active={filter}
              counts={countByFilter(conversations)}
              onChange={setFilter}
            />
            <LanguageFilterTabs
              active={language}
              options={languageOptions}
              onChange={setLanguage}
            />
          </div>
          {visible.length === 0 && (
            <p className="mt-8 text-muted">Nenhuma conversa corresponde ao filtro ou à busca.</p>
          )}
          <ul className="mt-4 divide-y divide-subtle overflow-hidden rounded-lg border border-subtle bg-surface">
            {visible.map((conversation) => (
              <ConversationRow key={conversation.id} conversation={conversation} now={now} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
