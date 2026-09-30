import { describe, expect, it } from "vitest";

import {
  formatClock,
  formatCustomerSince,
  formatLongDate,
  formatRelativeTime,
} from "../../src/lib/time";

const NOW = new Date("2026-09-28T15:00:00Z");
const TZ = "UTC";

describe("formatRelativeTime", () => {
  it.each([
    ["2026-09-28T14:59:40Z", "agora"],
    ["2026-09-28T14:56:00Z", "4 min"],
    ["2026-09-28T14:01:00Z", "59 min"],
    ["2026-09-28T12:00:00Z", "3 h"],
    ["2026-09-27T23:00:00Z", "16 h"],
    ["2026-09-27T09:00:00Z", "ontem"],
    ["2026-09-25T09:00:00Z", "3 d"],
    ["2026-09-10T09:00:00Z", "10 set"],
    ["2026-09-28T14:00:00Z", "1 h"],
    ["2026-09-27T15:00:00Z", "ontem"],
    ["2026-09-22T15:00:00Z", "6 d"],
    ["2026-09-21T15:00:00Z", "21 set"],
    ["2026-09-28T15:30:00Z", "agora"],
  ])("%s -> %s", (iso, expected) => {
    expect(formatRelativeTime(iso, NOW, TZ)).toBe(expected);
  });

  it("counts calendar days in the given time zone, not in UTC", () => {
    const message = "2026-09-27T02:00:00Z";

    expect(formatRelativeTime(message, NOW, "UTC")).toBe("ontem");
    // Em Fortaleza (UTC-3) a mensagem é de 26/09 às 23h: dois dias de calendário antes de hoje.
    expect(formatRelativeTime(message, NOW, "America/Fortaleza")).toBe("2 d");
  });

  it("counts hours (not 'ontem') for a message sent just before midnight", () => {
    const lateNight = new Date("2026-09-28T01:00:00Z");
    expect(formatRelativeTime("2026-09-27T23:30:00Z", lateNight, TZ)).toBe("1 h");
    expect(formatRelativeTime("2026-09-27T20:00:00Z", lateNight, TZ)).toBe("5 h");
  });
});

describe("date helpers", () => {
  it("formats the bubble clock as HH:mm", () => {
    expect(formatClock("2026-09-28T09:14:00Z", TZ)).toBe("09:14");
  });

  it("writes the long date with capitalized weekday and month", () => {
    expect(formatLongDate(NOW, TZ)).toBe("Segunda-feira, 28 de Setembro");
  });

  it("writes the customer-since date in lower case", () => {
    expect(formatCustomerSince("2026-09-22T10:00:00Z", TZ)).toBe("22 de setembro");
  });
});
