import type { ConversationStatus } from "../types";

const STATUS_LABELS: Record<ConversationStatus, string> = {
  aberta: "Aberta",
  precisa_atencao: "Precisa de atenção",
  resolvida: "Resolvida",
};

// Contraste WCAG (texto/fundo), calculado por scripts/check_design_tokens.py, claro | escuro:
//   Aberta              8,44:1 | 8,44:1
//   Precisa de atenção  5,75:1 | 7,22:1
//   Resolvida           8,20:1 | 5,71:1
// Todos acima do mínimo de 4,5:1 para texto normal; o estado também vai sempre em texto.
const STATUS_CLASSES: Record<ConversationStatus, string> = {
  aberta: "bg-accent-subtle text-accent-subtle",
  precisa_atencao: "bg-action-secondary text-on-action",
  resolvida: "bg-neutral-subtle text-neutral-subtle",
};

export function StatusBadge({ status }: Readonly<{ status: ConversationStatus }>) {
  return (
    <output
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${STATUS_CLASSES[status]}`}
    >
      {STATUS_LABELS[status]}
    </output>
  );
}
