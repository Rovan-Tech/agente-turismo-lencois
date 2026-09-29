import type { ConversationStatus } from "../types";

const STATUS_LABELS: Record<ConversationStatus, string> = {
  aberta: "Aberta",
  precisa_atencao: "Precisa de atenção",
  resolvida: "Resolvida",
};

const STATUS_CLASSES: Record<ConversationStatus, string> = {
  aberta: "bg-accent-subtle text-accent-subtle",
  precisa_atencao: "bg-action-secondary text-on-action",
  resolvida: "bg-neutral-subtle text-neutral-subtle",
};

export function StatusBadge({ status }: { status: ConversationStatus }) {
  return (
    <span
      role="status"
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${STATUS_CLASSES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
