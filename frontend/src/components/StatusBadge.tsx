import type { ConversationStatus } from "../types";

const STATUS_LABELS: Record<ConversationStatus, string> = {
  aberta: "Aberta",
  precisa_atencao: "Precisa de atenção",
  resolvida: "Resolvida",
};

const STATUS_CLASSES: Record<ConversationStatus, string> = {
  aberta: "bg-lagoa/10 text-lagoa",
  precisa_atencao: "bg-terracota text-white",
  resolvida: "bg-grafite/10 text-grafite",
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
