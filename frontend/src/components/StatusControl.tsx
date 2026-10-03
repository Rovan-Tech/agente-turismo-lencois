import type { ConversationStatus } from "../types";

const OPTIONS: ReadonlyArray<{ value: ConversationStatus; label: string; dot: string }> = [
  { value: "aberta", label: "Aberta", dot: "bg-action" },
  { value: "precisa_atencao", label: "Precisa de atenção", dot: "bg-action-secondary" },
  { value: "resolvida", label: "Resolvida", dot: "bg-neutral-subtle" },
];

/**
 * Mostra os três status, marca o atual e deixa a equipe trocar para qualquer outro (inclusive
 * reabrir uma conversa resolvida). O assistente ainda reavalia o status a cada nova mensagem.
 *
 * São botões com `aria-pressed` (e não `radio`): não há navegação por setas. `aria-disabled` (em
 * vez de `disabled`) mantém o foco no botão enquanto a requisição está em andamento.
 */
export function StatusControl({
  status,
  busy,
  onChange,
}: Readonly<{
  status: ConversationStatus;
  busy: boolean;
  onChange: (next: ConversationStatus) => void;
}>) {
  return (
    <fieldset aria-label="Status da conversa" className="min-w-0 flex flex-col gap-2">
      {OPTIONS.map(({ value, label, dot }) => {
        const selected = value === status;
        const canChoose = !selected && !busy;
        const tone = selected ? "border-focus bg-subtle" : "border-subtle bg-surface";
        return (
          <button
            key={value}
            type="button"
            aria-pressed={selected}
            aria-disabled={!canChoose}
            onClick={() => canChoose && onChange(value)}
            className={`flex items-center gap-2 rounded-md border px-3 py-2 text-left text-sm font-medium ${tone} ${
              canChoose || selected ? "text-primary" : "text-muted"
            } ${canChoose ? "hover:bg-subtle" : ""}`}
          >
            <span aria-hidden="true" className={`h-2 w-2 rounded-full ${dot}`} />
            {label}
          </button>
        );
      })}
    </fieldset>
  );
}
