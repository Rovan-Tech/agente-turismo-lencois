import { STATUS_FILTERS, type StatusFilter } from "../lib/conversations";

/** Abas de filtro por status; cada uma mostra quantas conversas tem. */
export function StatusFilterTabs({
  active,
  counts,
  onChange,
}: {
  active: StatusFilter;
  counts: Record<StatusFilter, number>;
  onChange: (filter: StatusFilter) => void;
}) {
  return (
    <div role="group" aria-label="Filtrar por status" className="flex flex-wrap gap-2">
      {STATUS_FILTERS.map(({ value, label }) => {
        const selected = value === active;
        return (
          <button
            key={value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(value)}
            className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold ${
              selected
                ? "border-transparent bg-action text-on-action"
                : "border-subtle bg-surface text-secondary hover:bg-subtle"
            }`}
          >
            {label}
            <span className="rounded-full bg-neutral-subtle px-2 text-xs text-neutral-subtle">
              {counts[value]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
