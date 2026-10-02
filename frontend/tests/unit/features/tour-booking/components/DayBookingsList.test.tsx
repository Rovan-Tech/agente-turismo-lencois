import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DayBookingsList } from "../../../../../src/features/tour-booking/components/DayBookingsList";
import { SAMPLE_BOOKING } from "../../../fixtures";

describe("DayBookingsList", () => {
  it("shows the date heading and each paid booking's details", () => {
    render(<DayBookingsList data="2026-09-28" bookings={[SAMPLE_BOOKING]} />);

    expect(
      screen.getByRole("heading", { name: "Agendamentos de 28 de setembro de 2026" })
    ).toBeInTheDocument();
    expect(screen.getByText("5598999998888")).toBeInTheDocument();
    expect(screen.getByText("3 pessoas · Pix")).toBeInTheDocument();
    expect(screen.getByText("Pago")).toBeInTheDocument();
  });

  it("says when a booking has no phone instead of leaving it blank", () => {
    render(
      <DayBookingsList data="2026-09-28" bookings={[{ ...SAMPLE_BOOKING, telefone: null }]} />
    );

    expect(screen.getByText("Telefone não informado")).toBeInTheDocument();
  });

  it("uses the singular for a single person", () => {
    render(<DayBookingsList data="2026-09-28" bookings={[{ ...SAMPLE_BOOKING, pessoas: 1 }]} />);

    expect(screen.getByText("1 pessoa · Pix")).toBeInTheDocument();
  });

  it("says there are no paid bookings yet, instead of showing an empty list", () => {
    render(<DayBookingsList data="2026-09-28" bookings={[]} />);

    expect(screen.getByText("Nenhum agendamento pago para este dia ainda.")).toBeInTheDocument();
  });
});
