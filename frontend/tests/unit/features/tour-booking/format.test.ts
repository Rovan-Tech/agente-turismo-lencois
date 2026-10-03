import { afterEach, describe, expect, it, vi } from "vitest";

import {
  dayOfMonth,
  formatDateLabel,
  formatMonthLabel,
  isoDateFromToday,
  occupancyLevel,
  paymentMethodLabel,
  remainingSeatsLabel,
} from "../../../../src/features/tour-booking/format";

describe("tour booking formatting", () => {
  it.each([
    [0, 41, "baixa"],
    [24, 41, "baixa"],
    [25, 41, "media"],
    [40, 41, "media"],
    [41, 41, "esgotado"],
    [45, 41, "esgotado"],
    [0, 0, "esgotado"],
    [6, 10, "media"],
  ] as const)("classifies %i/%i occupancy as %s", (ocupadas, capacidade, expected) => {
    expect(occupancyLevel(ocupadas, capacidade)).toBe(expected);
  });

  it.each([
    [39, 41, "2 vagas"],
    [40, 41, "1 vaga"],
    [41, 41, "Esgotado"],
    [50, 41, "Esgotado"],
  ])("labels %i/%i remaining seats as %s", (ocupadas, capacidade, expected) => {
    expect(remainingSeatsLabel(ocupadas, capacidade)).toBe(expected);
  });

  it.each([
    ["pix", "Pix"],
    ["boleto", "Boleto"],
    ["cartao", "Cartão"],
  ] as const)("labels the payment method %s as %s", (method, expected) => {
    expect(paymentMethodLabel(method)).toBe(expected);
  });

  it.each([
    ["2026-09-01", "1"],
    ["2026-09-28", "28"],
  ])("extracts the day of month from %s as %s", (isoDate, expected) => {
    expect(dayOfMonth(isoDate)).toBe(expected);
  });

  it("formats a full date label without shifting the day across time zones", () => {
    expect(formatDateLabel("2026-09-28")).toBe("28 de setembro de 2026");
  });

  it("formats a month label with a capitalized first letter", () => {
    expect(formatMonthLabel("2026-09")).toBe("Setembro de 2026");
  });
});

describe("isoDateFromToday", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it.each([
    [0, "2026-09-28"],
    [1, "2026-09-29"],
    [2, "2026-09-30"],
    [3, "2026-10-01"],
  ])("adds %i day(s) to 28/09/2026", (offset, expected) => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 8, 28, 23, 30, 0));

    expect(isoDateFromToday(offset)).toBe(expected);
  });

  it("rolls over the year", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 11, 31, 10, 0, 0));

    expect(isoDateFromToday(2)).toBe("2027-01-02");
  });
});
