import { useState, type FormEvent, type KeyboardEvent } from "react";

import { ErrorAlert } from "../../components/ErrorAlert";
import { PrimaryButton } from "../../components/PrimaryButton";
import { MAX_REPLY_LENGTH } from "../../lib/handoff";

/**
 * Campo de resposta do atendente. Sem `blockedReason` o campo vale; com ele (janela de 24 h
 * fechada) o campo fica desabilitado e o motivo aparece. O texto só é limpo quando o servidor
 * aceita, para uma falha não fazer a pessoa digitar tudo de novo.
 */
export function ReplyComposer({
  blockedReason,
  error,
  onSend,
}: {
  blockedReason: string | null;
  error: string | null;
  onSend: (text: string) => Promise<boolean>;
}) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const trimmed = text.trim();
  const canSend = !blockedReason && !sending && trimmed.length > 0;

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSend) return;
    setSending(true);
    const accepted = await onSend(trimmed);
    setSending(false);
    if (accepted) setText("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submit();
  }

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 border-t border-subtle px-4 py-4 sm:px-6"
    >
      <label htmlFor="reply-text" className="text-sm font-semibold text-primary">
        Resposta ao turista
      </label>
      <textarea
        id="reply-text"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        maxLength={MAX_REPLY_LENGTH}
        rows={3}
        disabled={Boolean(blockedReason)}
        aria-describedby="reply-help"
        className="rounded-md border border-subtle bg-surface p-2 text-primary disabled:bg-subtle disabled:text-muted"
      />
      <p id="reply-help" className="text-xs text-muted">
        {blockedReason ?? "Ctrl+Enter envia. A mensagem vai pelo WhatsApp como a agência."}
      </p>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted">
          {text.length}/{MAX_REPLY_LENGTH}
        </span>
        <PrimaryButton type="submit" disabled={!canSend}>
          {sending ? "Enviando…" : "Enviar"}
        </PrimaryButton>
      </div>
      {error && <ErrorAlert message={error} />}
    </form>
  );
}
