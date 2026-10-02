import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { TourBookingPage } from "../../src/pages/TourBookingPage";
import { SAMPLE_BOOKING, SAMPLE_DAY_OCCUPANCY } from "./fixtures";

const TODAY = "2026-09-28";

function daysOf(yearMonth: string, daysInMonth: number) {
  return Array.from({ length: daysInMonth }, (_, index) => ({
    ...SAMPLE_DAY_OCCUPANCY,
    data: `${yearMonth}-${String(index + 1).padStart(2, "0")}`,
  }));
}

function daysOfSeptember() {
  return daysOf("2026-09", 30);
}

function renderAt(id: string) {
  render(
    <MemoryRouter initialEntries={[`/passeios/${id}`]}>
      <Routes>
        <Route path="/passeios/:id" element={<TourBookingPage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 8, 28, 15, 0, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("TourBookingPage", () => {
  it("shows today's occupancy and the day's paid bookings once loaded", async () => {
    vi.spyOn(api, "getTourAgenda").mockResolvedValue(daysOfSeptember());
    vi.spyOn(api, "getDayBookings").mockResolvedValue([SAMPLE_BOOKING]);

    renderAt("passeio-bugre-orla");

    expect(
      await screen.findByText(
        `${SAMPLE_DAY_OCCUPANCY.capacidade - SAMPLE_DAY_OCCUPANCY.ocupadas} vagas`
      )
    ).toBeInTheDocument();
    expect(await screen.findByText("3 pessoas · Pix")).toBeInTheDocument();
  });

  it("shows an error when the calendar fails to load, instead of loading forever", async () => {
    vi.spyOn(api, "getTourAgenda").mockResolvedValue(null);
    vi.spyOn(api, "getDayBookings").mockResolvedValue([]);

    renderAt("passeio-bugre-orla");

    expect(
      await screen.findByText("Não foi possível carregar o calendário deste passeio.")
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Não foi possível carregar as vagas de hoje.")
    ).toBeInTheDocument();
  });

  it("keeps showing today's occupancy after navigating the calendar to another month", async () => {
    vi.spyOn(api, "getTourAgenda").mockImplementation(async (_id, mes) =>
      mes === "2026-09" ? daysOfSeptember() : daysOf("2026-10", 31)
    );
    vi.spyOn(api, "getDayBookings").mockResolvedValue([]);
    const todaySeats = `${SAMPLE_DAY_OCCUPANCY.capacidade - SAMPLE_DAY_OCCUPANCY.ocupadas} vagas`;

    renderAt("passeio-bugre-orla");
    await screen.findByText(todaySeats);

    fireEvent.click(screen.getByRole("button", { name: "Próximo mês" }));
    await waitFor(() =>
      expect(api.getTourAgenda).toHaveBeenLastCalledWith("passeio-bugre-orla", "2026-10")
    );

    expect(screen.getByText(todaySeats)).toBeInTheDocument();
  });

  it("shows an error when the day's bookings fail to load", async () => {
    vi.spyOn(api, "getTourAgenda").mockResolvedValue(daysOfSeptember());
    vi.spyOn(api, "getDayBookings").mockResolvedValue(null);

    renderAt("passeio-bugre-orla");

    expect(
      await screen.findByText("Não foi possível carregar os agendamentos deste dia.")
    ).toBeInTheDocument();
  });

  it("reloads the day's bookings when the attendant picks another day", async () => {
    const getDayBookings = vi
      .spyOn(api, "getDayBookings")
      .mockResolvedValueOnce([SAMPLE_BOOKING])
      .mockResolvedValueOnce([]);
    vi.spyOn(api, "getTourAgenda").mockResolvedValue(daysOfSeptember());

    renderAt("passeio-bugre-orla");
    await screen.findByText("3 pessoas · Pix");

    fireEvent.click(screen.getByRole("button", { name: /^Dia 5:/ }));

    await waitFor(() =>
      expect(getDayBookings).toHaveBeenLastCalledWith("passeio-bugre-orla", "2026-09-05")
    );
  });

  async function renderAndSubmitBooking() {
    vi.spyOn(api, "getTourAgenda").mockResolvedValue(daysOfSeptember());
    vi.spyOn(api, "getDayBookings").mockResolvedValue([]);
    renderAt("passeio-bugre-orla");
    await screen.findByText("Nenhum agendamento pago para este dia ainda.");
    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));
  }

  it("decrements the seats and lists the new booking right after a successful payment", async () => {
    vi.spyOn(api, "createBooking").mockResolvedValue({
      ok: true,
      data: { ...SAMPLE_BOOKING, data: TODAY, ocupadas: 13, capacidade: 41 },
    });

    await renderAndSubmitBooking();

    expect(await screen.findByText("28 vagas")).toBeInTheDocument();
    expect(await screen.findByText("3 pessoas · Pix")).toBeInTheDocument();
  });

  it("shows the server error when the booking cannot be created", async () => {
    vi.spyOn(api, "createBooking").mockResolvedValue({
      ok: false,
      status: 409,
      message: "não há vagas suficientes nesse dia",
    });

    await renderAndSubmitBooking();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "não há vagas suficientes nesse dia"
    );
  });
});
