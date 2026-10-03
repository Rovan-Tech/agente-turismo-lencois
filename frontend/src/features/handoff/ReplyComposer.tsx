import { useState, type FormEvent, type KeyboardEvent } from "react";

import { ErrorAlert } from "../../components/ErrorAlert";
import { PrimaryButton } from "../../components/PrimaryButton";
import { translateText } from "../../lib/api";
import { languageName } from "../../lib/conversations";
import { MAX_REPLY_LENGTH } from "../../lib/handoff";
import type { TargetLanguage } from "../../lib/schemas";

export const REPLY_FIELD_ID = "reply-text";

/**
 * Campo de resposta do atendente. Sem `blockedReason` o campo vale; com ele (janela de 24 h
 * fechada) o campo fica desabilitado e o motivo aparece. O texto só é limpo quando o servidor
 * aceita, para uma falha não fazer a pessoa digitar tudo de novo.
 *
 * Com `targetLanguage` (a conversa não está em português), o atendente escreve em português e
 * primeiro traduz: só depois de revisar a tradução o botão manda a mensagem, já no idioma do
 * turista. Sem `targetLanguage`, o comportamento é o de sempre (um clique, envia direto).
 */
export function ReplyComposer({
  blockedReason,
  error,
  onSend,
  targetLanguage,
}: Readonly<{
  blockedReason: string | null;
  error: string | null;
  onSend: (text: string) => Promise<boolean>;
  targetLanguage?: TargetLanguage;
}>) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);
  const [review, setReview] = useState<string | null>(null);
  const trimmed = text.trim();
  const busy = sending || translating;
  const canAct = !blockedReason && !busy && (review !== null || trimmed.length > 0);
  const targetName = targetLanguage ? languageName(targetLanguage) : null;

  function backToEditing() {
    setReview(null);
    setTranslateError(null);
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canAct) return;
    if (targetLanguage && review === null) {
      setTranslating(true);
      setTranslateError(null);
      const result = await translateText(trimmed, targetLanguage);
      setTranslating(false);
      if (result.ok) setReview(result.data);
      else setTranslateError("Não foi possível traduzir agora. Tente de novo.");
      return;
    }
    setSending(true);
    try {
      if (await onSend(review ?? trimmed)) {
        setText("");
        setReview(null);
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submit();
  }

  const buttonLabel = sending
    ? "Enviando…"
    : translating
      ? "Traduzindo…"
      : review !== null
        ? `Enviar em ${targetName}`
        : targetName
          ? `Traduzir para ${targetName}`
          : "Enviar";

  return (
    <form
      onSubmit={submit}
      className="flex shrink-0 flex-col gap-2 border-t border-subtle px-4 py-3 sm:py-4 sm:px-6"
    >
      <label htmlFor={REPLY_FIELD_ID} className="text-sm font-semibold text-primary">
        Resposta ao turista
      </label>
      <textarea
        id={REPLY_FIELD_ID}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        maxLength={MAX_REPLY_LENGTH}
        rows={2}
        disabled={Boolean(blockedReason) || review !== null}
        aria-describedby="reply-help"
        className="rounded-md border border-subtle bg-surface p-2 text-primary disabled:bg-subtle disabled:text-muted"
      />
      <p id="reply-help" className="text-xs text-muted">
        {blockedReason ?? "Ctrl+Enter envia. A mensagem vai pelo WhatsApp como a agência."}
      </p>
      {review !== null && (
        <div className="flex flex-col gap-1 rounded-md border border-subtle bg-subtle px-3 py-2 text-sm text-primary">
          <span className="text-xs font-semibold uppercase tracking-wide text-secondary">
            Será enviado em {targetName} · tradução da IA
          </span>
          {review}
        </div>
      )}
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted">
          {text.length}/{MAX_REPLY_LENGTH}
        </span>
        <div className="flex items-center gap-3">
          {review !== null && (
            <button
              type="button"
              onClick={backToEditing}
              className="text-sm font-semibold text-link hover:underline"
            >
              Voltar e editar
            </button>
          )}
          <PrimaryButton type="submit" disabled={!canAct}>
            {buttonLabel}
          </PrimaryButton>
        </div>
      </div>
      {translateError && <ErrorAlert message={translateError} />}
      {error && <ErrorAlert message={error} />}
    </form>
  );
}
