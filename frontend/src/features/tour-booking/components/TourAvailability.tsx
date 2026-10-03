import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ChevronRightIcon } from "../../../components/icons";
import { getTourAvailability } from "../../../lib/api";
import type { Tour, TourAvailability as Availability } from "../../../types";
import { difficultyLabel, formatDuration, formatPrice } from "../../suggested-tour/format";
import { isoDateFromToday } from "../format";
import { OccupancyBar } from "./OccupancyBar";

const DAYS = [
  { offset: 0, label: "Hoje" },
  { offset: 1, label: "Amanhã" },
  { offset: 2, label: "Depois de amanhã" },
] as const;

const CHIP = "rounded-full bg-neutral-subtle px-2 py-1 text-xs font-medium text-neutral-subtle";
const TAB_BASE = "rounded-full border px-4 py-2 text-sm font-semibold";
const TAB_SELECTED = "border-transparent bg-action text-on-action";
const TAB_IDLE = "border-subtle bg-surface text-secondary hover:bg-subtle";

type AvailabilityState =
  { status: "loading" } | { status: "error" } | { status: "ready"; items: Availability[] };

/**
 * Vagas de cada passeio ativo por dia (hoje, amanhã e depois de amanhã). Cada linha leva ao
 * detalhe do passeio, onde fica o calendário e o agendamento. Os dados do passeio vêm do catálogo
 * já carregado pela página; só as vagas (capacidade e pessoas pagas) vêm de `GET /api/tours/vagas`.
 */
export function TourAvailability({ tours }: Readonly<{ tours: Tour[] }>) {
  const [offset, setOffset] = useState<number>(0);
  const [state, setState] = useState<AvailabilityState>({ status: "loading" });
  const day = DAYS.find((option) => option.offset === offset) ?? DAYS[0];

  // Reativar/desativar um passeio na página muda quem tem vagas a mostrar: busca de novo.
  const activeIds = tours.map((tour) => tour.id).join(",");

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    getTourAvailability(isoDateFromToday(offset)).then((items) => {
      if (active) setState(items === null ? { status: "error" } : { status: "ready", items });
    });
    return () => {
      active = false;
    };
  }, [offset, activeIds]);

  const toursById = new Map(tours.map((tour) => [tour.id, tour]));
  const rows =
    state.status === "ready"
      ? state.items.flatMap((item) => {
          const tour = toursById.get(item.tour_id);
          return tour ? [{ tour, item }] : [];
        })
      : [];

  return (
    <section aria-labelledby="tour-availability-title" className="mt-6">
      <h2 id="tour-availability-title" className="font-display text-lg font-semibold text-primary">
        Vagas por dia
      </h2>
      <p className="mt-1 text-sm text-secondary">
        Atualizadas a cada agendamento confirmado e pago.
      </p>
      <fieldset aria-label="Dia das vagas" className="mt-3 flex min-w-0 flex-wrap gap-2">
        {DAYS.map(({ offset: value, label }) => (
          <DayTab
            key={value}
            label={label}
            selected={value === offset}
            onSelect={() => setOffset(value)}
          />
        ))}
      </fieldset>

      {state.status === "loading" && <p className="mt-4 text-muted">Carregando vagas…</p>}
      {state.status === "error" && (
        <p role="alert" className="mt-4 text-sm text-status-error">
          Não foi possível carregar as vagas.
        </p>
      )}
      {state.status === "ready" && <AvailabilityRows rows={rows} dayLabel={day.label} />}
    </section>
  );
}

interface Row {
  tour: Tour;
  item: Availability;
}

/** Linhas da lista: nome e dados do passeio à esquerda, barra de vagas à direita, tudo é um link. */
function AvailabilityRows({ rows, dayLabel }: Readonly<{ rows: Row[]; dayLabel: string }>) {
  return (
    <ul className="mt-4 divide-y divide-subtle rounded-lg border border-subtle bg-surface">
      {rows.map(({ tour, item }) => (
        <li key={tour.id}>
          <Link
            to={`/passeios/${tour.id}`}
            className="flex items-center gap-4 px-4 py-4 hover:bg-subtle"
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium text-primary">{tour.nome}</p>
              <ul className="mt-1 flex flex-wrap gap-2">
                <li className={CHIP}>{difficultyLabel(tour.dificuldade_fisica)}</li>
                <li className={CHIP}>{formatDuration(tour.duracao_horas)}</li>
                <li className={CHIP}>{formatPrice(tour.preco_reais)}</li>
              </ul>
            </div>
            <div className="w-40 shrink-0 sm:w-56">
              <OccupancyBar
                ocupadas={item.ocupadas}
                capacidade={item.capacidade}
                dayLabel={dayLabel.toLowerCase()}
              />
            </div>
            <ChevronRightIcon className="h-4 w-4 shrink-0 text-muted" />
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Aba de um dia: botão alternável (`aria-pressed`), com o selecionado em destaque. */
function DayTab({
  label,
  selected,
  onSelect,
}: Readonly<{ label: string; selected: boolean; onSelect: () => void }>) {
  return (
    <button
      className={`${TAB_BASE} ${selected ? TAB_SELECTED : TAB_IDLE}`}
      onClick={onSelect}
      aria-pressed={selected}
      type="button"
    >
      {label}
    </button>
  );
}
