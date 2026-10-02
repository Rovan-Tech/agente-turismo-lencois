import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

/** O modo demonstração é decidido por variável de build: cada teste recarrega os módulos com ela. */
async function load(env: Record<string, string>) {
  vi.resetModules();
  Object.entries(env).forEach(([name, value]) => vi.stubEnv(name, value));
  const [{ DemoBanner }, { UserMenu }, theme, { AppShell }] = await Promise.all([
    import("../../src/components/DemoBanner"),
    import("../../src/components/UserMenu"),
    import("../../src/lib/theme"),
    import("../../src/components/AppShell"),
  ]);
  return { DemoBanner, UserMenu, theme, AppShell };
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("demonstration mode", () => {
  it("says the data is fictional, that the assistant is scripted, and to ask Rovantech for a real demo", async () => {
    const { DemoBanner } = await load({ VITE_DEMO: "true" });

    render(<DemoBanner />);

    const note = screen.getByRole("note");
    expect(note).toHaveTextContent("Demonstração com dados fictícios. Nada é salvo.");
    expect(note).toHaveTextContent("exemplos fixos, não uma IA ao vivo");
    expect(note).toHaveTextContent("entre em contato com a Rovantech e solicite uma demonstração");
  });

  it("links to the Rovantech contact when one is configured", async () => {
    const { DemoBanner } = await load({
      VITE_DEMO: "true",
      VITE_DEMO_CONTACT_URL: "mailto:contato@exemplo.com",
    });

    render(<DemoBanner />);

    const link = screen.getByRole("link", { name: "Falar com a Rovantech" });
    expect(link).toHaveAttribute("href", "mailto:contato@exemplo.com");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("offers no contact button when none is configured, and keeps the text", async () => {
    const { DemoBanner } = await load({ VITE_DEMO: "true" });

    render(<DemoBanner />);

    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByRole("note")).toHaveTextContent("solicite uma demonstração");
  });

  it("puts the banner above the panel only in the demonstration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sem rede")));
    const real = await load({});
    const view = render(
      <MemoryRouter>
        <real.AppShell />
      </MemoryRouter>
    );
    expect(screen.queryByRole("note")).toBeNull();
    view.unmount();

    const demo = await load({ VITE_DEMO: "true" });
    render(
      <MemoryRouter>
        <demo.AppShell />
      </MemoryRouter>
    );
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("does not offer a sign out link: there is no login to leave", async () => {
    const { UserMenu } = await load({ VITE_DEMO: "true" });

    render(<UserMenu me={{ sub: "visitante", nome: "Visitante" }} />);

    expect(screen.getByText("Visitante")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sair" })).toBeNull();
  });

  it("does not remember the theme in the browser, and always starts light", async () => {
    window.localStorage.setItem("painel-tema", "dark");
    const { theme } = await load({ VITE_DEMO: "true" });
    const setItem = vi.spyOn(Storage.prototype, "setItem");

    theme.saveTheme("dark");

    expect(theme.getStoredTheme()).toBe("light");
    expect(setItem).not.toHaveBeenCalled();
  });

  it("keeps remembering the theme in the real panel", async () => {
    const { theme } = await load({});

    theme.saveTheme("dark");

    expect(theme.getStoredTheme()).toBe("dark");
  });
});

describe("safeContactUrl", () => {
  it.each([
    ["https://rovantech.com/contato", "https://rovantech.com/contato"],
    ["  mailto:contato@exemplo.com ", "mailto:contato@exemplo.com"],
    ["HTTPS://ROVANTECH.COM", "HTTPS://ROVANTECH.COM"],
    ["javascript:alert(1)", ""],
    ["http://sem-tls.example", ""],
    ["https://", ""],
    ["https://a b.example", ""],
    ["//rovantech.com", ""],
    ["", ""],
    [undefined, ""],
  ])("turns %j into %j", async (value, expected) => {
    const { safeContactUrl } = await import("../../src/lib/demo");

    expect(safeContactUrl(value)).toBe(expected);
  });
});
