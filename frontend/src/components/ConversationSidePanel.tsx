import type { ConversationStatus } from "../types";
import { StatusControl } from "./StatusControl";

const HEADING = "text-xs font-semibold uppercase tracking-wide text-secondary";

/** Painel lateral da conversa: status e ações. */
export function ConversationSidePanel({
  status,
  updating,
  updateFailed,
  onChange,
}: {
  status: ConversationStatus;
  updating: boolean;
  updateFailed: boolean;
  onChange: (next: ConversationStatus) => void;
}) {
  return (
    <aside
      aria-label="Detalhes da conversa"
      className="flex flex-col gap-4 border-t border-subtle bg-surface p-4 md:w-panel md:shrink-0 md:border-l md:border-t-0"
    >
      <h2 className={HEADING}>Status da conversa</h2>
      <StatusControl status={status} busy={updating} onChange={onChange} />
      <p className="text-xs text-muted">
        O assistente também atualiza o status quando o turista escreve de novo.
      </p>
      {status !== "resolvida" && (
        <button
          type="button"
          onClick={() => onChange("resolvida")}
          disabled={updating}
          className="rounded-md border border-subtle px-4 py-2 text-sm font-medium text-primary hover:bg-subtle active:bg-subtle disabled:bg-subtle disabled:text-muted"
        >
          {updating ? "Salvando…" : "Marcar como resolvida"}
        </button>
      )}
      {updateFailed && (
        <p role="alert" className="text-sm text-status-error">
          Não foi possível alterar o status. Tente novamente.
        </p>
      )}
    </aside>
  );
}
