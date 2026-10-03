import { ErrorAlert } from "../../components/ErrorAlert";
import { PrimaryButton } from "../../components/PrimaryButton";
import type { ConversationHeader, Me } from "../../types";

/** Ids dos botões: a página leva o foco a um deles quando a troca de estado desmonta o outro. */
export const TAKE_OVER_ID = "take-over-button";
export const GIVE_BACK_ID = "give-back-button";
const BLOCKED_REASON_ID = "take-over-blocked-reason";

const BUTTON =
  "rounded-md border border-subtle px-4 py-2 text-sm font-medium text-primary hover:bg-subtle active:bg-subtle disabled:bg-subtle disabled:text-muted";

/** O que o turista vai ler no aviso de que uma pessoa assumiu (o nome vem do login). */
function announcementPreview(me: Me | null): string {
  if (me === null) return "O turista será avisado de que uma pessoa da nossa equipe está falando.";
  return me.nome
    ? `O turista verá o aviso com o seu nome: ${me.nome}.`
    : "O turista será avisado de que uma pessoa da equipe está falando, sem nome (o seu login não tem um primeiro nome utilizável).";
}

function holderName(conversation: ConversationHeader): string {
  return conversation.atendente_nome ?? "outra pessoa da equipe";
}

function holderLabel(conversation: ConversationHeader, isMine: boolean): string {
  return isMine ? "Você está atendendo" : `Atendendo: ${holderName(conversation)}`;
}

/** Por que quem não é o atendente não pode assumir (o servidor também recusa com 409). */
function TakeOverBlockedNotice({ conversation }: Readonly<{ conversation: ConversationHeader }>) {
  return (
    <>
      <p id={BLOCKED_REASON_ID} className="text-xs text-muted">
        Você não pode assumir: a conversa já está com {holderName(conversation)}. Quem atende
        precisa devolver à IA primeiro (ou devolva você, se a conversa ficou esquecida).
      </p>
      <button type="button" disabled aria-describedby={BLOCKED_REASON_ID} className={BUTTON}>
        Assumir conversa
      </button>
    </>
  );
}

/** Quem responde esta conversa e os botões para assumir ou devolver para a IA. */
export function HandoffSection({
  conversation,
  me,
  busy,
  error,
  onTakeOver,
  onGiveBack,
}: Readonly<{
  conversation: ConversationHeader;
  me: Me | null;
  busy: boolean;
  error: string | null;
  onTakeOver: () => void;
  onGiveBack: () => void;
}>) {
  const isHandled = conversation.atendimento === "humano";
  const isMine = isHandled && me !== null && conversation.atendente_sub === me.sub;
  return (
    <section aria-label="Atendimento" className="flex flex-col gap-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-secondary">Atendimento</h2>
      {isHandled ? (
        <>
          <p className="text-sm font-semibold text-primary">{holderLabel(conversation, isMine)}</p>
          <p className="text-xs text-muted">O assistente de IA não responde enquanto isso.</p>
          {!isMine && <TakeOverBlockedNotice conversation={conversation} />}
          <button
            id={GIVE_BACK_ID}
            type="button"
            onClick={onGiveBack}
            disabled={busy}
            className={BUTTON}
          >
            {busy ? "Devolvendo…" : "Devolver para a IA"}
          </button>
        </>
      ) : (
        <>
          <p className="text-sm text-primary">O assistente de IA responde esta conversa.</p>
          {conversation.status === "resolvida" ? (
            <p className="text-xs text-muted">Reabra a conversa para assumir.</p>
          ) : (
            <>
              <p className="text-xs text-muted">{announcementPreview(me)}</p>
              <PrimaryButton id={TAKE_OVER_ID} onClick={onTakeOver} disabled={busy}>
                {busy ? "Assumindo…" : "Assumir conversa"}
              </PrimaryButton>
            </>
          )}
        </>
      )}
      {error && <ErrorAlert message={error} />}
    </section>
  );
}
