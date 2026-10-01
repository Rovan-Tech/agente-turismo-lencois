import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { TourList } from "../../src/components/TourList";
import type { Tour } from "../../src/types";
import { SAMPLE_TOUR } from "./fixtures";

function renderList(overrides: Partial<React.ComponentProps<typeof TourList>> = {}) {
  render(
    <MemoryRouter>
      <TourList tours={[SAMPLE_TOUR]} onEdit={vi.fn()} onToggleActive={vi.fn()} {...overrides} />
    </MemoryRouter>
  );
}

describe("TourList", () => {
  it("renders each tour with its badge and price", () => {
    renderList();

    expect(screen.getByText("Passeio de bugre")).toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*100,00 · 2\.5h/)).toBeInTheDocument();
  });

  it("links to the booking page of each tour", () => {
    renderList();

    expect(screen.getByRole("link", { name: "Agendamentos" })).toHaveAttribute(
      "href",
      "/passeios/passeio-bugre-orla"
    );
  });

  it("shows Reativar for an inactive tour and calls onToggleActive", () => {
    const onToggleActive = vi.fn();
    const inactiveTour: Tour = { ...SAMPLE_TOUR, ativo: false };
    renderList({ tours: [inactiveTour], onToggleActive });

    fireEvent.click(screen.getByRole("button", { name: "Reativar" }));

    expect(onToggleActive).toHaveBeenCalledWith(inactiveTour);
  });

  it("calls onEdit with the clicked tour", () => {
    const onEdit = vi.fn();
    renderList({ onEdit });

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(onEdit).toHaveBeenCalledWith(SAMPLE_TOUR);
  });
});
