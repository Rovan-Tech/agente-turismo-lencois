import type { ReactNode } from "react";

import type { Delta } from "../format";

/** Um indicador: rótulo, valor grande, texto de apoio e, se houver período anterior, o delta. */
export function KpiCard({
  label,
  value,
  sub,
  delta,
  hero = false,
}: Readonly<{
  label: string;
  value: ReactNode;
  sub: string;
  delta: Delta | null;
  hero?: boolean;
}>) {
  return (
    <article
      className={`flex flex-col gap-2 rounded-lg border border-subtle bg-surface p-5 ${hero ? "sm:col-span-2" : ""}`}
    >
      <span className="text-sm font-semibold text-secondary">{label}</span>
      <span className={`font-display font-semibold text-primary ${hero ? "text-6xl" : "text-3xl"}`}>
        {value}
      </span>
      <span className="text-sm text-secondary">{sub}</span>
      {delta && (
        <span
          className={`text-sm font-semibold ${delta.positivo ? "text-status-success" : "text-status-error"}`}
        >
          {delta.texto}
        </span>
      )}
    </article>
  );
}
