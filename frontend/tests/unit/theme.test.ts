import { afterEach, describe, expect, it, vi } from "vitest";

import { applyTheme, getStoredTheme, saveTheme } from "../../src/lib/theme";

describe("theme", () => {
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    vi.restoreAllMocks();
  });

  it("defaults to the light theme, ignoring the system preference", () => {
    expect(getStoredTheme()).toBe("light");
  });

  it.each(["light", "dark"] as const)("remembers the chosen %s theme", (theme) => {
    saveTheme(theme);

    expect(getStoredTheme()).toBe(theme);
  });

  it("falls back to light when the stored value is not a known theme", () => {
    window.localStorage.setItem("painel-tema", "roxo");

    expect(getStoredTheme()).toBe("light");
  });

  it("marks the page with the theme so the tokens switch", () => {
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("still works when the browser blocks storage (private mode)", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });

    expect(getStoredTheme()).toBe("light");
    expect(() => saveTheme("dark")).not.toThrow();
  });
});
