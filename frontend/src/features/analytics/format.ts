export function formatInt(value: number): string {
  return Math.round(value).toLocaleString("pt-BR");
}

export function formatPercent(value: number): string {
  return value.toFixed(1).replace(".", ",") + "%";
}

export type DeltaKind = "pct" | "pp" | "min";

export interface Delta {
  texto: string;
  positivo: boolean;
}

/**
 * Compara o valor atual com o do período anterior. `good` diz qual direção é a boa notícia
 * (`"up"` para conversão e vendas; `"down"` para o tempo de 1ª resposta) — só isso decide a cor,
 * nunca o sinal da seta sozinho.
 */
export function delta(
  atual: number,
  anterior: number | null,
  kind: DeltaKind,
  good: "up" | "down"
): Delta | null {
  if (anterior === null || anterior === 0) return null;
  const diff = kind === "pct" ? ((atual - anterior) / anterior) * 100 : atual - anterior;
  const up = diff >= 0;
  const sinal = up ? "+" : "";
  const unidade = kind === "pct" ? "%" : kind === "pp" ? " p.p." : " min";
  const seta = up ? "▲" : "▼";
  const texto = `${seta} ${sinal}${diff.toFixed(1).replace(".", ",")}${unidade} vs. período anterior`;
  return { texto, positivo: good === "up" ? up : !up };
}

export const PERIOD_LABELS: Record<number, string> = { 7: "7 dias", 30: "30 dias", 90: "90 dias" };

/**
 * Classe de fundo de uma célula do mapa de calor, relativa ao maior valor da grade inteira.
 *
 * O sistema de design só tem uma escala semântica de destaque (`accent-subtle`), sem uma rampa de
 * vários tons — então o "calor" vira três passos discretos dela em vez dos seis tons do desenho; o
 * número de conversas, sempre visível na célula, é que carrega a leitura fina, não a cor.
 */
export function heatClass(value: number, max: number): string {
  if (value <= 0 || max <= 0) return "bg-page text-muted";
  const ratio = value / max;
  if (ratio < 0.34) return "bg-subtle text-primary";
  if (ratio < 0.67) return "bg-accent-subtle text-accent-subtle";
  return "bg-action text-on-action";
}
