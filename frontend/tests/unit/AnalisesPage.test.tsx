import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { AnalisesPage } from "../../src/pages/AnalisesPage";
import { SAMPLE_ANALYTICS } from "./fixtures";

function renderPage() {
  render(<AnalisesPage />);
}

describe("AnalisesPage", () => {
  it("shows an error state when the API call fails", async () => {
    vi.spyOn(api, "getAnalytics").mockResolvedValue(null);
    renderPage();

    expect(await screen.findByText("Não foi possível carregar as análises.")).toBeInTheDocument();
  });

  it("shows the conversion rate, the KPIs and the period picker", async () => {
    vi.spyOn(api, "getAnalytics").mockResolvedValue(SAMPLE_ANALYTICS);
    renderPage();

    expect(await screen.findByText("20,0%")).toBeInTheDocument();
    expect(screen.getByText("20 vendas em 100 conversas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "30 dias" })).toHaveAttribute("aria-pressed", "true");
  });

  it("refetches with the new period when the person picks another one", async () => {
    const getAnalytics = vi.spyOn(api, "getAnalytics").mockResolvedValue(SAMPLE_ANALYTICS);
    renderPage();
    await screen.findByText("20,0%");

    fireEvent.click(screen.getByRole("button", { name: "7 dias" }));

    await waitFor(() => expect(getAnalytics).toHaveBeenLastCalledWith(7));
  });

  it("renders each ranking section and the heatmap", async () => {
    vi.spyOn(api, "getAnalytics").mockResolvedValue(SAMPLE_ANALYTICS);
    renderPage();
    await screen.findByText("20,0%");

    expect(screen.getByText("O que aconteceu com as conversas")).toBeInTheDocument();
    expect(screen.getByText("Quem atendeu")).toBeInTheDocument();
    expect(screen.getByText("Conversas atendidas por pessoa")).toBeInTheDocument();
    expect(screen.getByText("Passeios: o que mais e o que menos sai")).toBeInTheDocument();
    expect(screen.getByText("Idiomas dos turistas")).toBeInTheDocument();
    expect(screen.getByText("Quando as conversas chegam")).toBeInTheDocument();
  });
});
