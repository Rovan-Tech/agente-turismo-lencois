import type { Analytics } from "../../../types";
import { formatInt, heatClass } from "../format";

/** Conversas por dia da semana e faixa de horário; o número na célula, nunca só a cor. */
export function Heatmap({ mapa }: Readonly<{ mapa: Analytics["mapa_calor"] }>) {
  const max = Math.max(1, ...mapa.valores.flat());
  return (
    <section
      aria-labelledby="t-horas"
      className="flex flex-col gap-4 rounded-lg border border-subtle bg-surface p-5"
    >
      <div>
        <h2 id="t-horas" className="font-display text-lg font-semibold text-primary">
          Quando as conversas chegam
        </h2>
        <p className="mt-1 text-sm text-secondary">
          Dia da semana e faixa de horário (hora local da agência). Use para escalar a equipe nos
          horários de pico.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-center text-sm">
          <caption className="sr-only">Conversas por dia da semana e faixa de horário</caption>
          <thead>
            <tr>
              <th scope="col" className="p-1 text-left text-xs font-semibold text-secondary">
                Dia
              </th>
              {mapa.faixas.map((faixa) => (
                <th key={faixa} scope="col" className="p-1 text-xs font-semibold text-secondary">
                  {faixa}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mapa.dias.map((dia, dayIndex) => (
              <tr key={dia}>
                <th scope="row" className="p-1 text-left text-xs font-semibold text-secondary">
                  {dia}
                </th>
                {mapa.valores[dayIndex].map((valor, hourIndex) => (
                  <td key={mapa.faixas[hourIndex]} className="p-1">
                    <span
                      className={`block rounded px-1 py-2 font-semibold tabular-nums ${heatClass(valor, max)}`}
                    >
                      {formatInt(valor)}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
