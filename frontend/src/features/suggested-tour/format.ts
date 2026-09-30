import type { DifficultyLevel } from "../../types";

const LOCALE = "pt-BR";

const DIFFICULTY_LABELS: Record<DifficultyLevel, string> = {
  baixa: "Dificuldade baixa",
  media: "Dificuldade média",
  alta: "Dificuldade alta",
};

export function difficultyLabel(level: DifficultyLevel): string {
  return DIFFICULTY_LABELS[level];
}

/** Duração do passeio: "1h", "2,5h". */
export function formatDuration(hours: number): string {
  return `${hours.toLocaleString(LOCALE, { maximumFractionDigits: 1 })}h`;
}

/** Preço por pessoa sem centavos quando é inteiro: "R$ 120", "R$ 99,90", "R$ 1.200". */
export function formatPrice(reais: number): string {
  const digits = Number.isInteger(reais) ? 0 : 2;
  const amount = reais.toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: 2,
  });
  return `R$ ${amount}`;
}
