import { describe, expect, it } from "vitest";

import {
  difficultyLabel,
  formatDuration,
  formatPrice,
} from "../../../../src/features/suggested-tour/format";

describe("suggested tour formatting", () => {
  it.each([
    [1, "1h"],
    [2.5, "2,5h"],
    [0.5, "0,5h"],
    [3, "3h"],
  ])("formats %s hours as %s", (hours, expected) => {
    expect(formatDuration(hours)).toBe(expected);
  });

  it.each([
    [120, "R$ 120"],
    [99.9, "R$ 99,90"],
    [1200, "R$ 1.200"],
    [0, "R$ 0"],
  ])("formats the price %s as %s", (reais, expected) => {
    expect(formatPrice(reais)).toBe(expected);
  });

  it.each([
    ["baixa", "Dificuldade baixa"],
    ["media", "Dificuldade média"],
    ["alta", "Dificuldade alta"],
  ] as const)("labels the difficulty %s", (level, expected) => {
    expect(difficultyLabel(level)).toBe(expected);
  });
});
