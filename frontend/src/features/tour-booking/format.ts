import type { PaymentMethod } from "../../types";

const LOCALE = "pt-BR";

export type OccupancyLevel = "baixa" | "media" | "esgotado";

const MEDIUM_THRESHOLD = 0.6;

/** Nível de ocupação de um dia, para colorir a barra e as células do calendário. */
export function occupancyLevel(ocupadas: number, capacidade: number): OccupancyLevel {
  if (capacidade <= 0 || ocupadas >= capacidade) return "esgotado";
  const ratio = ocupadas / capacidade;
  return ratio >= MEDIUM_THRESHOLD ? "media" : "baixa";
}

const OCCUPANCY_BADGE_CLASS: Record<OccupancyLevel, string> = {
  baixa: "bg-occupancy-low text-occupancy-low",
  media: "bg-occupancy-medium text-occupancy-medium",
  esgotado: "bg-occupancy-full text-occupancy-full",
};

/** Classes Tailwind (tokens) do selo/célula de um nível de ocupação. */
export function occupancyBadgeClass(level: OccupancyLevel): string {
  return OCCUPANCY_BADGE_CLASS[level];
}

/** "12 vagas", "1 vaga" ou "Esgotado", conforme as vagas restantes do dia. */
export function remainingSeatsLabel(ocupadas: number, capacidade: number): string {
  const remaining = capacidade - ocupadas;
  if (remaining <= 0) return "Esgotado";
  return remaining === 1 ? "1 vaga" : `${remaining} vagas`;
}

const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  pix: "Pix",
  boleto: "Boleto",
  cartao: "Cartão",
};

/** Rótulo em pt-BR de uma forma de pagamento simulada ("pix" → "Pix"). */
export function paymentMethodLabel(method: PaymentMethod): string {
  return PAYMENT_METHOD_LABELS[method];
}

/** Dia do mês ("28") a partir de uma data `YYYY-MM-DD`, sem passar por fuso horário. */
export function dayOfMonth(isoDate: string): string {
  return String(Number(isoDate.split("-")[2]));
}

/** Data por extenso ("28 de setembro de 2026") a partir de `YYYY-MM-DD`, sem conversão de fuso. */
export function formatDateLabel(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.toLocaleDateString(LOCALE, {
    timeZone: "UTC",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Nome do mês por extenso ("Setembro de 2026") a partir de `YYYY-MM`. */
export function formatMonthLabel(yearMonth: string): string {
  const [year, month] = yearMonth.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, 1));
  const label = date.toLocaleDateString(LOCALE, {
    timeZone: "UTC",
    month: "long",
    year: "numeric",
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
}
