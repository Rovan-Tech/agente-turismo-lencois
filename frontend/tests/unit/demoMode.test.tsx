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
  it("shows the fictional data notice and links to the real WhatsApp when a number is configured", async () => {
    const { DemoBanner } = await load({
      VITE_DEMO: "true",
      VITE_DEMO_WHATSAPP: "+55 11 90000-0000",
    });

    render(<DemoBanner />);

    expect(screen.getByRole("note")).toHaveTextContent(
      "Demonstração com dados fictícios. Nada é salvo."
    );
    const link = screen.getByRole("link", { name: "Conversar com o assistente de verdade" });
    expect(link).toHaveAttribute("href", "https://wa.me/5511900000000");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("offers no contact button when no WhatsApp number is configured", async () => {
    const { DemoBanner } = await load({ VITE_DEMO: "true" });

    render(<DemoBanner />);

    expect(screen.queryByRole("link")).toBeNull();
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
