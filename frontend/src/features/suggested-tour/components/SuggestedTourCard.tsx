import type { SuggestedTour } from "../../../types";
import { difficultyLabel, formatDuration, formatPrice } from "../format";

const CHIP = "rounded-full px-2 py-1 text-xs font-medium";

/** Passeio do catálogo que o assistente recomendou; sem sugestão, diz isso em vez de sumir. */
export function SuggestedTourCard({ tour }: { tour: SuggestedTour | null }) {
  return (
    <section aria-labelledby="suggested-tour-title" className="flex flex-col gap-2">
      <h2
        id="suggested-tour-title"
        className="text-xs font-semibold uppercase tracking-wide text-secondary"
      >
        Passeio sugerido pela IA
      </h2>
      {tour ? (
        <div className="flex flex-col gap-2 rounded-md border border-subtle bg-surface p-3">
          <p className="font-display font-semibold text-primary">{tour.nome}</p>
          <p className="text-sm text-secondary">{tour.descricao}</p>
          <ul className="flex flex-wrap gap-2">
            <li className={`${CHIP} bg-accent-subtle text-accent-subtle`}>
              {difficultyLabel(tour.dificuldade_fisica)}
            </li>
            <li className={`${CHIP} bg-neutral-subtle text-neutral-subtle`}>
              {formatDuration(tour.duracao_horas)}
            </li>
            {tour.acessivel_cadeirantes && (
              <li className={`${CHIP} bg-neutral-subtle text-neutral-subtle`}>
                Acessível p/ cadeirantes
              </li>
            )}
            {tour.acessivel_idosos && (
              <li className={`${CHIP} bg-neutral-subtle text-neutral-subtle`}>
                Acessível p/ idosos
              </li>
            )}
            {tour.acessivel_criancas_pequenas && (
              <li className={`${CHIP} bg-neutral-subtle text-neutral-subtle`}>
                Acessível p/ crianças pequenas
              </li>
            )}
          </ul>
          <p className="text-sm text-muted">
            <strong className="text-base text-primary">{formatPrice(tour.preco_reais)}</strong>{" "}
            <span>por pessoa</span>
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted">A IA ainda não sugeriu um passeio nesta conversa.</p>
      )}
    </section>
  );
}
