import { PERIOD_LABELS } from "../format";

/** Escolha do período (7/30/90 dias); as opções vêm do backend, não de uma lista fixa aqui. */
export function PeriodPicker({
  options,
  active,
  onChange,
}: Readonly<{ options: readonly number[]; active: number; onChange: (days: number) => void }>) {
  return (
    <div
      role="group"
      aria-label="Período"
      className="flex gap-1 rounded-md border border-subtle bg-surface p-1"
    >
      {options.map((days) => {
        const selected = days === active;
        return (
          <button
            key={days}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(days)}
            className={`min-h-10 rounded px-4 text-sm font-semibold ${
              selected ? "bg-action text-on-action" : "text-primary hover:bg-subtle"
            }`}
          >
            {PERIOD_LABELS[days] ?? `${days} dias`}
          </button>
        );
      })}
    </div>
  );
}
