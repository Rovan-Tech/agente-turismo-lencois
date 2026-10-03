import type { AnalyticsBar } from "../../../types";
import { formatInt } from "../format";

/** Uma lista ordenada com barra relativa ao maior valor (destinos, idiomas, passeios, equipe…). */
export function RankingList({
  title,
  description,
  rows,
}: Readonly<{ title: string; description: string; rows: readonly AnalyticsBar[] }>) {
  const max = Math.max(1, ...rows.map((row) => row.quantidade));
  return (
    <section
      aria-label={title}
      className="flex flex-col gap-4 rounded-lg border border-subtle bg-surface p-5"
    >
      <div>
        <h2 className="font-display text-lg font-semibold text-primary">{title}</h2>
        <p className="mt-1 text-sm text-secondary">{description}</p>
      </div>
      {rows.length === 0 && <p className="text-sm text-muted">Sem dados neste período.</p>}
      <ul className="flex flex-col gap-3">
        {rows.map((row) => (
          <li key={row.rotulo} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-semibold text-primary">{row.rotulo}</span>
              <span className="text-sm font-semibold text-primary">
                {formatInt(row.quantidade)}
                {row.percentual !== null && ` · ${row.percentual.toFixed(0)}%`}
              </span>
            </div>
            <progress
              value={row.quantidade}
              max={max}
              aria-label={`${row.rotulo}: ${formatInt(row.quantidade)}`}
              className="h-3 w-full appearance-none overflow-hidden rounded-full bg-neutral-subtle [&::-webkit-progress-bar]:bg-neutral-subtle [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-action [&::-moz-progress-bar]:rounded-full [&::-moz-progress-bar]:bg-action"
            />
            {row.sub && <span className="text-xs text-muted">{row.sub}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
