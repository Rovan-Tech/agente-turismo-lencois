import { useRef } from "react";
import { Link, useParams } from "react-router-dom";

import { SuggestedTourCard } from "../features/suggested-tour/components/SuggestedTourCard";
import { HandoffSection } from "../features/handoff/HandoffSection";
import { ReplyComposer } from "../features/handoff/ReplyComposer";
import { useConversationActions } from "../features/handoff/useConversationActions";
import { useConversationDetail } from "../features/handoff/useConversationDetail";
import { useMe } from "../features/handoff/useMe";
import { ConversationSidePanel } from "../components/ConversationSidePanel";
import { LanguageAvatar } from "../components/LanguageAvatar";
import { MessageBubble } from "../components/MessageBubble";
import { StatusBadge } from "../components/StatusBadge";
import { ChevronLeftIcon } from "../components/icons";
import { formatPhone, languageName } from "../lib/conversations";
import { WINDOW_CLOSED_NOTICE, isReplyWindowOpen } from "../lib/handoff";
import { formatCustomerSince } from "../lib/time";
import type { ConversationDetail } from "../types";

function ConversationHeaderBar({
  conversation,
  titleRef,
}: {
  conversation: ConversationDetail;
  titleRef: React.RefObject<HTMLHeadingElement>;
}) {
  const language = languageName(conversation.idioma_detectado);
  return (
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
  );
}

export function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [conversation, setConversation, reload] = useConversationDetail(id);
  const me = useMe();
  // O botão "Marcar como resolvida" sai da tela: leva o foco ao título para não se perder.
  const actions = useConversationActions(id, setConversation, reload, () =>
    titleRef.current?.focus()
  );
  const isMine =
    conversation?.atendimento === "humano" && me !== null && conversation.atendente_sub === me.sub;

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
            <ConversationHeaderBar conversation={conversation} titleRef={titleRef} />
            <ul className="flex flex-col gap-4 px-4 py-6 sm:px-6">
              {conversation.messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </ul>
            {isMine && (
              <ReplyComposer
                blockedReason={
                  isReplyWindowOpen(conversation.messages, new Date()) ? null : WINDOW_CLOSED_NOTICE
                }
                error={actions.replyError}
                onSend={actions.sendReply}
              />
            )}
          </>
        )}
      </section>

      {conversation && (
        <ConversationSidePanel
          status={conversation.status}
          updating={actions.busy}
          updateFailed={actions.statusFailed}
          onChange={actions.changeStatus}
        >
          <HandoffSection
            conversation={conversation}
            me={me}
            busy={actions.busy}
            error={actions.handoffError}
            onTakeOver={actions.takeOver}
            onGiveBack={actions.giveBack}
          />
          <SuggestedTourCard tour={conversation.passeio_sugerido} />
        </ConversationSidePanel>
      )}
    </main>
  );
}
