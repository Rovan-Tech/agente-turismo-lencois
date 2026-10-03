import { occupancyBadgeClass, occupancyLevel, remainingSeatsLabel } from "../format";

// Classes estáticas (Tailwind só gera CSS pro que lê como texto literal no fonte). O preenchimento
// do `<progress>` nativo é pintado pelos pseudo-elementos do WebKit/Blink e do Firefox; sem estilo
// inline (FE-4) e só com tokens de cor.
const FILL_CLASS: Record<ReturnType<typeof occupancyLevel>, string> = {
  baixa: "[&::-webkit-progress-value]:bg-occupancy-low [&::-moz-progress-bar]:bg-occupancy-low",
  media:
    "[&::-webkit-progress-value]:bg-occupancy-medium [&::-moz-progress-bar]:bg-occupancy-medium",
  esgotado:
    "[&::-webkit-progress-value]:bg-occupancy-full [&::-moz-progress-bar]:bg-occupancy-full",
};

/** Ocupação de hoje: barra de progresso mais o selo "X vagas" (nunca só cor, a leitura é textual). */
export function OccupancyBar({
  ocupadas,
  capacidade,
}: Readonly<{ ocupadas: number; capacidade: number }>) {
  const level = occupancyLevel(ocupadas, capacidade);
  const percent = capacidade > 0 ? Math.min(100, Math.round((ocupadas / capacidade) * 100)) : 100;
  const label = remainingSeatsLabel(ocupadas, capacidade);

  return (
    <div className="flex flex-col gap-1">
      <progress
        value={percent}
        max={100}
        aria-label={`Ocupação de hoje: ${label}`}
        className={`h-2 w-full appearance-none overflow-hidden rounded-full bg-neutral-subtle [&::-webkit-progress-bar]:bg-neutral-subtle [&::-webkit-progress-value]:rounded-full [&::-moz-progress-bar]:rounded-full ${FILL_CLASS[level]}`}
      />
      <span
        className={`w-fit rounded-full px-2 py-1 text-xs font-medium ${occupancyBadgeClass(level)}`}
      >
        {label}
      </span>
    </div>
  );
}
