import { occupancyBadgeClass, occupancyLevel, remainingSeatsLabel } from "../format";

const BAR_CLASS: Record<ReturnType<typeof occupancyLevel>, string> = {
  baixa: "bg-occupancy-low",
  media: "bg-occupancy-medium",
  esgotado: "bg-occupancy-full",
};

// Classes estáticas (Tailwind só gera CSS pro que lê como texto literal no fonte): a largura é
// arredondada pro degrau de 5% mais próximo em vez de ir por `style={{ width }}` (FE-4: sem
// estilo inline novo).
const WIDTH_CLASSES = [
  "w-[0%]",
  "w-[5%]",
  "w-[10%]",
  "w-[15%]",
  "w-[20%]",
  "w-[25%]",
  "w-[30%]",
  "w-[35%]",
  "w-[40%]",
  "w-[45%]",
  "w-[50%]",
  "w-[55%]",
  "w-[60%]",
  "w-[65%]",
  "w-[70%]",
  "w-[75%]",
  "w-[80%]",
  "w-[85%]",
  "w-[90%]",
  "w-[95%]",
  "w-[100%]",
] as const;
const WIDTH_STEP = 5;

function widthClass(percent: number): string {
  const clamped = Math.min(100, Math.max(0, percent));
  const index = Math.round(clamped / WIDTH_STEP);
  return WIDTH_CLASSES[index];
}

/** Ocupação de hoje: barra de progresso mais o selo "X vagas" (nunca só cor, a leitura é textual). */
export function OccupancyBar({ ocupadas, capacidade }: { ocupadas: number; capacidade: number }) {
  const level = occupancyLevel(ocupadas, capacidade);
  const percent = capacidade > 0 ? Math.min(100, Math.round((ocupadas / capacidade) * 100)) : 100;
  const label = remainingSeatsLabel(ocupadas, capacidade);

  return (
    <div className="flex flex-col gap-1">
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Ocupação de hoje: ${label}`}
        className="h-2 w-full overflow-hidden rounded-full bg-neutral-subtle"
      >
        <div
          className={`h-full rounded-full transition-all ${BAR_CLASS[level]} ${widthClass(percent)}`}
        />
      </div>
      <span
        className={`w-fit rounded-full px-2 py-1 text-xs font-medium ${occupancyBadgeClass(level)}`}
      >
        {label}
      </span>
    </div>
  );
}
