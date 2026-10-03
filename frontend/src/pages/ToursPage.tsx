import { useState } from "react";

import { TourForm } from "../components/TourForm";
import { TourCardGrid } from "../features/tour-booking/components/TourCardGrid";
import { createTour, deleteTour, listTours, updateTour } from "../lib/api";
import { useFetchState } from "../lib/useFetchState";
import type { Tour } from "../types";

type FormMode = { kind: "closed" } | { kind: "create" } | { kind: "edit"; tour: Tour };

export function ToursPage() {
  const [toursState, reload] = useFetchState(() => listTours(true));
  const [formMode, setFormMode] = useState<FormMode>({ kind: "closed" });
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleToggleActive(tour: Tour) {
    setActionError(null);
    const result = tour.ativo
      ? await deleteTour(tour.id)
      : await updateTour(tour.id, { ...tour, ativo: true });

    if (result.ok) {
      await reload();
    } else {
      setActionError(result.message);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-primary">Passeios</h1>
          <p className="mt-1 text-sm text-secondary">
            Veja as vagas de cada passeio por dia e cuide do catálogo que o assistente oferece aos
            turistas.
          </p>
        </div>
        {formMode.kind === "closed" && (
          <button
            type="button"
            onClick={() => setFormMode({ kind: "create" })}
            className="rounded-md bg-action px-4 py-2 text-sm font-medium text-on-action hover:bg-action-hover active:bg-action-active"
          >
            Novo passeio
          </button>
        )}
      </div>

      {actionError && (
        <p role="alert" className="mt-4 text-sm text-status-error">
          {actionError}
        </p>
      )}

      {formMode.kind !== "closed" && (
        <TourForm
          key={formMode.kind === "edit" ? formMode.tour.id : "create"}
          mode={formMode.kind}
          initialTour={formMode.kind === "edit" ? formMode.tour : undefined}
          onSubmit={(payload) =>
            formMode.kind === "create" ? createTour(payload) : updateTour(payload.id, payload)
          }
          onSuccess={() => {
            setFormMode({ kind: "closed" });
            reload();
          }}
          onCancel={() => setFormMode({ kind: "closed" })}
        />
      )}

      {toursState.status === "loading" && <p className="mt-8 text-muted">Carregando…</p>}

      {toursState.status === "error" && (
        <p role="alert" className="mt-8 text-sm text-status-error">
          Não foi possível carregar os passeios.
        </p>
      )}

      {toursState.status === "ready" && toursState.data.length === 0 && (
        <p className="mt-8 text-muted">Nenhum passeio cadastrado.</p>
      )}

      {toursState.status === "ready" && toursState.data.length > 0 && (
        <TourCardGrid
          tours={toursState.data}
          onEdit={(tour) => setFormMode({ kind: "edit", tour })}
          onToggleActive={handleToggleActive}
        />
      )}
    </main>
  );
}
