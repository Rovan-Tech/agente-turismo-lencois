import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ActiveBadge } from "../../../components/ActiveBadge";
import { getTourAvailability } from "../../../lib/api";
import type { Tour, TourAvailability as Availability } from "../../../types";
import { formatDuration, formatPrice } from "../../suggested-tour/format";
import { isoDateFromToday } from "../format";
import { OccupancyBar } from "./OccupancyBar";

const DAYS = [
  { offset: 0, label: "Hoje" },
  { offset: 1, label: "Amanhã" },
  { offset: 2, label: "Depois de amanhã" },
] as const;

const TAB_BASE = "min-h-11 rounded-full border px-4 text-sm font-semibold";
const TAB_SELECTED = "border-transparent bg-action text-on-action";
const TAB_IDLE = "border-subtle bg-surface text-secondary hover:bg-subtle";

type AvailabilityState =
  { status: "loading" } | { status: "error" } | { status: "ready"; items: Availability[] };

/**
 * Catálogo de passeios em grade de cards: vagas do dia escolhido, estado ativo/desativado e as
 * ações (agendamentos, editar, ativar/desativar). Substitui a antiga dupla lista+vagas por uma
 * única visão, como no desenho do redesign.
 */
export function TourCardGrid({
  tours,
  onEdit,
  onToggleActive,
}: Readonly<{
  tours: Tour[];
  onEdit: (tour: Tour) => void;
  onToggleActive: (tour: Tour) => void;
}>) {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<AvailabilityState>({ status: "loading" });
  const day = DAYS.find((option) => option.offset === offset) ?? DAYS[0];
  const activeIds = tours
    .filter((tour) => tour.ativo)
    .map((tour) => tour.id)
    .join(",");

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

  const availabilityByTour = new Map(
    state.status === "ready" ? state.items.map((item) => [item.tour_id, item] as const) : []
  );
  const summary = summarize(tours, availabilityByTour);

  return (
    <section aria-label="Lista de passeios" className="mt-6 flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <fieldset aria-label="Escolher o dia" className="flex flex-wrap gap-2">
          {DAYS.map(({ offset: value, label }) => (
            <button
              key={value}
              type="button"
              aria-pressed={value === offset}
              onClick={() => setOffset(value)}
              className={`${TAB_BASE} ${value === offset ? TAB_SELECTED : TAB_IDLE}`}
            >
              {label}
            </button>
          ))}
        </fieldset>
        {state.status === "ready" && <DaySummary {...summary} />}
      </div>

      {state.status === "loading" && <p className="text-muted">Carregando vagas…</p>}
      {state.status === "error" && (
        <p role="alert" className="text-sm text-status-error">
          Não foi possível carregar as vagas.
        </p>
      )}

      <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {tours.map((tour) => (
          <TourCard
            key={tour.id}
            tour={tour}
            item={availabilityByTour.get(tour.id)}
            dayLabel={day.label}
            onEdit={onEdit}
            onToggleActive={onToggleActive}
          />
        ))}
      </ul>
    </section>
  );
}

function summarize(
  tours: readonly Tour[],
  availabilityByTour: ReadonlyMap<string, Availability>
): { freeSpots: number; soldOut: number } {
  let freeSpots = 0;
  let soldOut = 0;
  for (const tour of tours) {
    if (!tour.ativo) continue;
    const item = availabilityByTour.get(tour.id);
    if (!item) continue;
    freeSpots += Math.max(0, item.capacidade - item.ocupadas);
    if (item.ocupadas >= item.capacidade) soldOut += 1;
  }
  return { freeSpots, soldOut };
}

function DaySummary({ freeSpots, soldOut }: Readonly<{ freeSpots: number; soldOut: number }>) {
  return (
    <div className="flex items-center gap-6 text-sm text-secondary">
      <span>
        <strong className="font-display text-2xl text-primary">{freeSpots}</strong> vagas livres
        neste dia
      </span>
      <span>
        <strong className="font-display text-2xl text-primary">{soldOut}</strong> passeios esgotados
      </span>
    </div>
  );
}

function TourCard({
  tour,
  item,
  dayLabel,
  onEdit,
  onToggleActive,
}: Readonly<{
  tour: Tour;
  item: Availability | undefined;
  dayLabel: string;
  onEdit: (tour: Tour) => void;
  onToggleActive: (tour: Tour) => void;
}>) {
  return (
    <li className="flex flex-col gap-4 rounded-lg border border-subtle bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-xl font-semibold text-primary">{tour.nome}</h2>
        <ActiveBadge ativo={tour.ativo} />
      </div>
      <p className="text-sm text-muted">
        {formatPrice(tour.preco_reais)} · {formatDuration(tour.duracao_horas)}
      </p>

      {tour.ativo && item && (
        <OccupancyBar
          ocupadas={item.ocupadas}
          capacidade={item.capacidade}
          dayLabel={dayLabel.toLowerCase()}
        />
      )}
      {!tour.ativo && (
        <p className="text-sm text-secondary">
          Desativado: o assistente não oferece este passeio e ele não recebe reservas.
        </p>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-4 border-t border-subtle pt-3 text-sm">
        {tour.ativo && (
          <Link to={`/passeios/${tour.id}`} className="font-semibold text-link hover:underline">
            Agendamentos
          </Link>
        )}
        <button
          type="button"
          onClick={() => onEdit(tour)}
          className="font-semibold text-link hover:underline"
        >
          Editar
        </button>
        <button
          type="button"
          onClick={() => onToggleActive(tour)}
          className="font-semibold text-link hover:underline"
        >
          {tour.ativo ? "Desativar" : "Reativar"}
        </button>
      </div>
    </li>
  );
}
