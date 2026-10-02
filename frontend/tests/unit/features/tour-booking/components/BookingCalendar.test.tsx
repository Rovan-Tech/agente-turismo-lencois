import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BookingCalendar } from "../../../../../src/features/tour-booking/components/BookingCalendar";
import { SAMPLE_DAY_OCCUPANCY } from "../../../fixtures";

const DAYS = [SAMPLE_DAY_OCCUPANCY, { data: "2026-09-29", capacidade: 41, ocupadas: 41 }];

function renderCalendar(overrides: Partial<React.ComponentProps<typeof BookingCalendar>> = {}) {
  const onSelectDate = vi.fn();
  const onChangeMonth = vi.fn();
  render(
    <BookingCalendar
      yearMonth="2026-09"
      days={DAYS}
      selectedDate="2026-09-28"
      onSelectDate={onSelectDate}
      onChangeMonth={onChangeMonth}
      {...overrides}
    />
  );
  return { onSelectDate, onChangeMonth };
}

describe("BookingCalendar", () => {
  it("shows the month label and a button per day with the remaining seats", () => {
    renderCalendar();

    expect(screen.getByRole("heading", { name: "Setembro de 2026" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dia 28: 31 vagas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dia 29: Esgotado" })).toBeInTheDocument();
  });

  it("marks the selected day as pressed for assistive technology", () => {
    renderCalendar();

    expect(screen.getByRole("button", { name: "Dia 28: 31 vagas" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: "Dia 29: Esgotado" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("calls onSelectDate with the clicked day's date", () => {
    const { onSelectDate } = renderCalendar();

    fireEvent.click(screen.getByRole("button", { name: "Dia 29: Esgotado" }));

    expect(onSelectDate).toHaveBeenCalledWith("2026-09-29");
  });

  it("calls onChangeMonth with the adjacent month when navigating", () => {
    const { onChangeMonth } = renderCalendar();

    fireEvent.click(screen.getByRole("button", { name: "Próximo mês" }));
    expect(onChangeMonth).toHaveBeenCalledWith("2026-10");

    fireEvent.click(screen.getByRole("button", { name: "Mês anterior" }));
    expect(onChangeMonth).toHaveBeenCalledWith("2026-08");
  });
});
