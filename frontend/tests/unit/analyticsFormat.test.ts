import { describe, expect, it } from "vitest";

import { delta, formatInt, formatPercent, heatClass } from "../../src/features/analytics/format";

describe("formatInt", () => {
  it("formats with pt-BR thousands separators", () => {
    expect(formatInt(1234)).toBe("1.234");
  });
});

describe("formatPercent", () => {
  it("formats with a comma and one decimal", () => {
    expect(formatPercent(21.05)).toBe("21,1%");
    expect(formatPercent(21)).toBe("21,0%");
  });
});

describe("delta", () => {
  it("returns null without a previous value to compare", () => {
    expect(delta(10, null, "pct", "up")).toBeNull();
    expect(delta(10, 0, "pct", "up")).toBeNull();
  });

  it("marks a percentage increase as positive when up is good", () => {
    const result = delta(110, 100, "pct", "up");
    expect(result?.positivo).toBe(true);
    expect(result?.texto).toContain("▲");
    expect(result?.texto).toContain("+10,0%");
  });

  it("marks a drop in minutes as positive when down is good", () => {
    const result = delta(5, 10, "min", "down");
    expect(result?.positivo).toBe(true);
    expect(result?.texto).toContain("▼");
    expect(result?.texto).toContain("-5,0 min");
  });

  it("marks an increase in minutes as negative when down is good", () => {
    const result = delta(12, 10, "min", "down");
    expect(result?.positivo).toBe(false);
  });

  it("uses percentage points for pp deltas", () => {
    const result = delta(71, 67, "pp", "up");
    expect(result?.texto).toContain("+4,0 p.p.");
  });
});

describe("heatClass", () => {
  it("is the empty tone for zero or an empty grid", () => {
    expect(heatClass(0, 10)).toContain("bg-page");
    expect(heatClass(5, 0)).toContain("bg-page");
  });

  it("steps up as the value approaches the grid's max", () => {
    expect(heatClass(1, 10)).toContain("bg-subtle");
    expect(heatClass(5, 10)).toContain("bg-accent-subtle");
    expect(heatClass(10, 10)).toContain("bg-action");
  });
});
