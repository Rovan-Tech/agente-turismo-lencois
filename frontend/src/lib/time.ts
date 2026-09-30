const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const LOCALE = "pt-BR";

/** Meia-noite do dia local de `date`, para comparar dias de calendário (não janelas de 24 h). */
function startOfDay(date: Date, timeZone?: string): number {
  const parts = new Intl.DateTimeFormat(LOCALE, {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const value = (type: string) => Number(parts.find((part) => part.type === type)?.value);
  return Date.UTC(value("year"), value("month") - 1, value("day"));
}

/** "agora", "4 min", "3 h" (até 24 h), "ontem", "3 d" ou, depois de uma semana, "22 set". */
export function formatRelativeTime(iso: string, now: Date, timeZone?: string): string {
  const date = new Date(iso);
  const elapsed = now.getTime() - date.getTime();
  if (elapsed < MINUTE_MS) return "agora";
  if (elapsed < HOUR_MS) return `${Math.floor(elapsed / MINUTE_MS)} min`;
  if (elapsed < DAY_MS) return `${Math.floor(elapsed / HOUR_MS)} h`;
  const days = Math.round((startOfDay(now, timeZone) - startOfDay(date, timeZone)) / DAY_MS);
  if (days === 1) return "ontem";
  if (days < 7) return `${days} d`;
  return date
    .toLocaleDateString(LOCALE, { timeZone, day: "numeric", month: "short" })
    .replace(".", "")
    .replace(" de ", " ");
}

/** Horário do balão de mensagem, ex.: "09:14". */
export function formatClock(iso: string, timeZone?: string): string {
  return new Date(iso).toLocaleTimeString(LOCALE, {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Data por extenso do topo do painel, ex.: "Segunda-feira, 28 de Setembro". */
export function formatLongDate(now: Date, timeZone?: string): string {
  const text = now.toLocaleDateString(LOCALE, {
    timeZone,
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  return text
    .split(" ")
    .map((word) => (word === "de" ? word : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}

/** "22 de setembro": desde quando a pessoa conversa com a agência. */
export function formatCustomerSince(iso: string, timeZone?: string): string {
  return new Date(iso).toLocaleDateString(LOCALE, { timeZone, day: "numeric", month: "long" });
}
