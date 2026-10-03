import { Link } from "react-router-dom";

import { ActiveBadge } from "./ActiveBadge";
import type { Tour } from "../types";

const CURRENCY_FORMATTER = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

interface TourListProps {
  tours: Tour[];
  onEdit: (tour: Tour) => void;
  onToggleActive: (tour: Tour) => void;
}

export function TourList({ tours, onEdit, onToggleActive }: Readonly<TourListProps>) {
  return (
    <ul className="mt-6 divide-y divide-subtle rounded-lg border border-subtle bg-surface">
      {tours.map((tour) => (
        <li key={tour.id} className="flex items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="font-medium text-primary">{tour.nome}</p>
            <p className="text-sm text-muted">
              {CURRENCY_FORMATTER.format(tour.preco_reais)} · {tour.duracao_horas}h
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ActiveBadge ativo={tour.ativo} />
            {tour.ativo && (
              <Link to={`/passeios/${tour.id}`} className="text-sm text-link hover:underline">
                Agendamentos
              </Link>
            )}
            <button
              type="button"
              onClick={() => onEdit(tour)}
              className="text-sm text-link hover:underline"
            >
              Editar
            </button>
            <button
              type="button"
              onClick={() => onToggleActive(tour)}
              className="text-sm text-link hover:underline"
            >
              {tour.ativo ? "Desativar" : "Reativar"}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
