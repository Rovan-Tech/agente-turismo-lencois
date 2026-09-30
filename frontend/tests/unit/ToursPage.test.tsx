import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ToursPage } from "../../src/pages/ToursPage";
import { fillTourFormRequiredFields, SAMPLE_TOUR as ACTIVE_TOUR } from "./fixtures";

async function renderWithSingleTour() {
  vi.spyOn(api, "listTours").mockResolvedValue([ACTIVE_TOUR]);
  render(<ToursPage />);
  await screen.findByText("Passeio de bugre");
}

const SECOND_TOUR = { ...ACTIVE_TOUR, id: "passeio-vale-do-paraiso", nome: "Vale do Paraíso" };

describe("ToursPage", () => {
  it("shows an error when the catalog fails to load", async () => {
    vi.spyOn(api, "listTours").mockResolvedValue(null);

    render(<ToursPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar os passeios."
    );
  });

  it("shows an empty state when there are no tours", async () => {
    vi.spyOn(api, "listTours").mockResolvedValue([]);

    render(<ToursPage />);

    expect(await screen.findByText("Nenhum passeio cadastrado.")).toBeInTheDocument();
  });

  it("lists tours with their active status", async () => {
    vi.spyOn(api, "listTours").mockResolvedValue([ACTIVE_TOUR]);

    render(<ToursPage />);

    expect(await screen.findByText("Passeio de bugre")).toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
  });

  it("creates a new tour and reloads the list", async () => {
    vi.spyOn(api, "listTours").mockResolvedValueOnce([]).mockResolvedValueOnce([ACTIVE_TOUR]);
    vi.spyOn(api, "createTour").mockResolvedValue({ ok: true, data: ACTIVE_TOUR });

    render(<ToursPage />);
    await screen.findByText("Nenhum passeio cadastrado.");

    fireEvent.click(screen.getByRole("button", { name: "Novo passeio" }));
    fillTourFormRequiredFields("passeio-bugre-orla", "Passeio de bugre");
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(api.createTour).toHaveBeenCalled());
    expect(await screen.findByText("Passeio de bugre")).toBeInTheDocument();
  });

  it("shows the correct tour's data when switching which one is being edited", async () => {
    vi.spyOn(api, "listTours").mockResolvedValue([ACTIVE_TOUR, SECOND_TOUR]);

    render(<ToursPage />);
    await screen.findByText("Passeio de bugre");

    const editButtons = screen.getAllByRole("button", { name: "Editar" });

    fireEvent.click(editButtons[0]);
    expect(screen.getByLabelText("Nome")).toHaveValue("Passeio de bugre");

    fireEvent.click(editButtons[1]);
    expect(screen.getByLabelText("Nome")).toHaveValue("Vale do Paraíso");
  });

  it("edits an existing tour", async () => {
    const updated = { ...ACTIVE_TOUR, preco_reais: 150 };
    vi.spyOn(api, "updateTour").mockResolvedValue({ ok: true, data: updated });

    await renderWithSingleTour();

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText("Preço (R$)"), { target: { value: "150" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() =>
      expect(api.updateTour).toHaveBeenCalledWith(
        "passeio-bugre-orla",
        expect.objectContaining({ preco_reais: 150 })
      )
    );
  });

  it("deactivates a tour successfully and reloads the list", async () => {
    const inactiveTour = { ...ACTIVE_TOUR, ativo: false };
    vi.spyOn(api, "listTours")
      .mockResolvedValueOnce([ACTIVE_TOUR])
      .mockResolvedValueOnce([inactiveTour]);
    vi.spyOn(api, "deleteTour").mockResolvedValue({ ok: true, data: inactiveTour });

    render(<ToursPage />);
    await screen.findByText("Passeio de bugre");

    fireEvent.click(screen.getByRole("button", { name: "Desativar" }));

    await waitFor(() => expect(api.deleteTour).toHaveBeenCalledWith("passeio-bugre-orla"));
    expect(await screen.findByText("Inativo")).toBeInTheDocument();
  });

  it("closes the form without submitting when Cancelar is clicked", async () => {
    const updateTour = vi.spyOn(api, "updateTour");

    await renderWithSingleTour();

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("form")).not.toBeInTheDocument();
    expect(updateTour).not.toHaveBeenCalled();
  });

  it("shows an error when deactivating a tour fails", async () => {
    vi.spyOn(api, "deleteTour").mockResolvedValue({
      ok: false,
      status: 500,
      message: "falha ao desativar",
    });

    await renderWithSingleTour();

    fireEvent.click(screen.getByRole("button", { name: "Desativar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("falha ao desativar");
  });
});
