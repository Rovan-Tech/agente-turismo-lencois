import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TourAvailability } from "../../../../../src/features/tour-booking/components/TourAvailability";
import * as api from "../../../../../src/lib/api";
import type { Tour, TourAvailability as Availability } from "../../../../../src/types";
import { SAMPLE_TOUR } from "../../../fixtures";

const BARCO = { ...SAMPLE_TOUR, id: "passeio-barco", nome: "Passeio de barco" };
const TRILHA = { ...SAMPLE_TOUR, id: "trilha-das-lagoas", nome: "Trilha das Lagoas" };

function availability(...items: [string, number, number][]): Availability[] {
  return items.map(([tour_id, capacidade, ocupadas]) => ({ tour_id, capacidade, ocupadas }));
}

const inRouter = (tours: Tour[]) => (
  <MemoryRouter>
    <TourAvailability tours={tours} />
  </MemoryRouter>
);

const renderTours = (tours = [SAMPLE_TOUR, BARCO, TRILHA]) => render(inRouter(tours));

const TODAY = new Date(2026, 8, 28, 15);
beforeEach(() => void vi.useFakeTimers({ toFake: ["Date"], now: TODAY }));
afterEach(() => void vi.useRealTimers());

describe("TourAvailability", () => {
  it("loads today's seats first and shows the three occupancy levels with a text label", async () => {
    const spy = vi
      .spyOn(api, "getTourAvailability")
      .mockResolvedValue(
        availability(
          ["passeio-bugre-orla", 40, 5],
          ["passeio-barco", 30, 26],
          ["trilha-das-lagoas", 20, 20]
        )
      );

    renderTours();

    expect(screen.getByText("Carregando vagas…")).toBeInTheDocument();
    expect(await screen.findByText("35 vagas")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith("2026-09-28");
    expect(screen.getByText("4 vagas")).toBeInTheDocument();
    expect(screen.getByText("Esgotado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hoje" })).toHaveAttribute("aria-pressed", "true");
  });

  it("colors each row by its own occupancy, with the thresholds at 60% and 100%", async () => {
    vi.spyOn(api, "getTourAvailability").mockResolvedValue(
      availability(
        ["passeio-bugre-orla", 10, 5],
        ["passeio-barco", 10, 6],
        ["trilha-das-lagoas", 10, 10]
      )
    );

    renderTours();

    expect(await screen.findByText("5 vagas")).toHaveClass("bg-occupancy-low");
    expect(screen.getByText("4 vagas")).toHaveClass("bg-occupancy-medium");
    expect(screen.getByText("Esgotado")).toHaveClass("bg-occupancy-full");
  });

  it("switches the day tab, asks for that day and reads the new numbers", async () => {
    const spy = vi
      .spyOn(api, "getTourAvailability")
      .mockImplementation(async (dia) =>
        dia === "2026-09-28"
          ? availability(["passeio-bugre-orla", 30, 0])
          : availability(["passeio-bugre-orla", 30, 30])
      );

    renderTours([SAMPLE_TOUR]);
    expect(await screen.findByText("30 vagas")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Amanhã" }));
    expect(await screen.findByText("Esgotado")).toBeInTheDocument();
    expect(spy).toHaveBeenLastCalledWith("2026-09-29");
    expect(screen.getByRole("button", { name: "Amanhã" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Hoje" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("progressbar", { name: "Ocupação de amanhã: Esgotado" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Depois de amanhã" }));
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith("2026-09-30"));
    expect(
      await screen.findByRole("progressbar", { name: "Ocupação de depois de amanhã: Esgotado" })
    ).toBeVisible();
  });

  it("links every row to the tour's detail page", async () => {
    vi.spyOn(api, "getTourAvailability").mockResolvedValue(
      availability(["passeio-bugre-orla", 30, 0])
    );

    renderTours([SAMPLE_TOUR]);

    const link = await screen.findByRole("link", { name: /Passeio de bugre/ });
    expect(link).toHaveAttribute("href", "/passeios/passeio-bugre-orla");
    expect(within(link).getByText("Dificuldade baixa")).toBeInTheDocument();
    expect(within(link).getByText("2,5h")).toBeInTheDocument();
    expect(within(link).getByText("R$ 100")).toBeInTheDocument();
  });

  it("keeps the order the API sent and skips seats of tours it does not know", async () => {
    vi.spyOn(api, "getTourAvailability").mockResolvedValue(
      availability(
        ["trilha-das-lagoas", 10, 1],
        ["desconhecido", 10, 1],
        ["passeio-bugre-orla", 10, 2]
      )
    );

    renderTours();

    await screen.findByText("9 vagas");
    const names = screen.getAllByRole("link").map((link) => link.textContent ?? "");
    expect(names).toHaveLength(2);
    expect(names[0]).toContain("Trilha das Lagoas");
    expect(names[1]).toContain("Passeio de bugre");
  });

  it("shows an alert when the seats cannot be loaded", async () => {
    vi.spyOn(api, "getTourAvailability").mockResolvedValue(null);

    renderTours();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar as vagas."
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("ignores a slow answer for a day the user already left", async () => {
    let resolveToday: (value: Availability[]) => void = () => undefined;
    vi.spyOn(api, "getTourAvailability").mockImplementation((dia) =>
      dia === "2026-09-28"
        ? new Promise((resolve) => {
            resolveToday = resolve;
          })
        : Promise.resolve(availability(["passeio-bugre-orla", 30, 30]))
    );

    renderTours([SAMPLE_TOUR]);
    fireEvent.click(screen.getByRole("button", { name: "Amanhã" }));
    expect(await screen.findByText("Esgotado")).toBeInTheDocument();

    await act(async () => resolveToday(availability(["passeio-bugre-orla", 30, 0])));

    expect(screen.getByText("Esgotado")).toBeInTheDocument();
    expect(screen.queryByText("30 vagas")).not.toBeInTheDocument();
  });

  it("asks again when the set of active tours changes", async () => {
    const spy = vi
      .spyOn(api, "getTourAvailability")
      .mockResolvedValue(availability(["passeio-bugre-orla", 30, 0]));

    const { rerender } = renderTours([SAMPLE_TOUR]);
    await screen.findByText("30 vagas");

    rerender(inRouter([SAMPLE_TOUR, BARCO]));

    await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  });
});
