import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TourList } from "../../src/components/TourList";
import { SAMPLE_TOUR } from "./fixtures";

describe("TourList", () => {
  it("renders each tour with its badge and price", () => {
    render(<TourList tours={[SAMPLE_TOUR]} onEdit={vi.fn()} onToggleActive={vi.fn()} />);

    expect(screen.getByText("Passeio de bugre")).toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*100,00 · 2\.5h/)).toBeInTheDocument();
  });

  it("shows Reativar for an inactive tour and calls onToggleActive", () => {
    const onToggleActive = vi.fn();
    render(
      <TourList
        tours={[{ ...SAMPLE_TOUR, ativo: false }]}
        onEdit={vi.fn()}
        onToggleActive={onToggleActive}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Reativar" }));

    expect(onToggleActive).toHaveBeenCalledWith({ ...SAMPLE_TOUR, ativo: false });
  });

  it("calls onEdit with the clicked tour", () => {
    const onEdit = vi.fn();
    render(<TourList tours={[SAMPLE_TOUR]} onEdit={onEdit} onToggleActive={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(onEdit).toHaveBeenCalledWith(SAMPLE_TOUR);
  });
});
