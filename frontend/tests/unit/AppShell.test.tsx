import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../../src/components/AppShell";
import * as api from "../../src/lib/api";

function renderShellAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<p>página inicial</p>} />
          <Route path="/conversas/:id" element={<p>página da conversa</p>} />
          <Route path="/passeios" element={<p>página de passeios</p>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

/** Links da barra lateral (desktop); o cabeçalho do celular tem outra navegação. */
function sidebarNav() {
  return within(screen.getByRole("complementary", { name: "Barra lateral" }));
}

describe("AppShell", () => {
  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("starts in the light theme and switches to dark (and back) with the toggle", () => {
    renderShellAt("/");
    expect(document.documentElement.dataset.theme).toBe("light");

    fireEvent.click(screen.getAllByRole("button", { name: "Usar modo escuro" })[0]);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("painel-tema")).toBe("dark");

    fireEvent.click(screen.getAllByRole("button", { name: "Usar modo claro" })[0]);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("keeps both toggles (top bar and mobile header) in sync", () => {
    renderShellAt("/");

    fireEvent.click(screen.getAllByRole("button", { name: "Usar modo escuro" })[0]);

    expect(screen.queryAllByRole("button", { name: "Usar modo escuro" })).toHaveLength(0);
    expect(screen.getAllByRole("button", { name: "Usar modo claro" })).toHaveLength(2);
  });

  it("does not store a theme until the person actually chooses one", () => {
    renderShellAt("/");

    expect(window.localStorage.getItem("painel-tema")).toBeNull();
  });

  it("restores the theme the person chose last time", () => {
    window.localStorage.setItem("painel-tema", "dark");

    renderShellAt("/");

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("renders the routed page inside the shell with the brand and the AI indicator", () => {
    renderShellAt("/");

    expect(screen.getByText("página inicial")).toBeInTheDocument();
    expect(screen.getAllByText("Vento Branco Expedições").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Painel do agente").length).toBeGreaterThan(0);
    expect(screen.getByText("Assistente de IA respondendo agora")).toBeInTheDocument();
    expect(screen.getByText("Equipe")).toBeInTheDocument();
  });

  it("fits the open conversation to the window height, while other pages grow with content", () => {
    renderShellAt("/conversas/abc123");
    const shell = screen.getByText("página da conversa").closest("div.flex.flex-col.bg-page");
    expect(shell).toHaveClass("h-dvh");
    expect(shell).not.toHaveClass("min-h-screen");
    cleanup();

    renderShellAt("/passeios");
    const other = screen.getByText("página de passeios").closest("div.flex.flex-col.bg-page");
    expect(other).toHaveClass("min-h-screen");
    expect(other).not.toHaveClass("h-dvh");
  });

  it("shows today's date in the top bar", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 8, 28, 15, 0, 0)); // hora local: o dia não depende do fuso

    renderShellAt("/");

    expect(screen.getByText("Segunda-feira, 28 de Setembro")).toBeInTheDocument();
  });

  it.each([
    ["/", "Conversas"],
    ["/conversas/abc", "Conversas"],
    ["/passeios", "Passeios"],
  ])("marks the section of %s as the current page in the navigation", (path, current) => {
    renderShellAt(path);

    const links = sidebarNav().getAllByRole("link");
    const marked = links.filter((link) => link.getAttribute("aria-current") === "page");
    expect(marked.map((link) => link.textContent)).toEqual([current]);
  });

  describe("who is logged in", () => {
    const SIGN_OUT = { name: "Sair" };

    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it("shows the person's first name and a link that ends the Access session", async () => {
      vi.spyOn(api, "getMe").mockResolvedValue({ sub: "pessoa-1", nome: "Ana" });

      renderShellAt("/");

      expect(await screen.findByText("Ana")).toBeInTheDocument();
      expect(screen.queryByText("Equipe")).toBeNull();
      const links = screen.getAllByRole("link", SIGN_OUT);
      expect(links.map((link) => link.getAttribute("href"))).toEqual([
        "/cdn-cgi/access/logout",
        "/cdn-cgi/access/logout",
      ]);
    });

    it("keeps the generic name, with the sign out link, when the login has no usable first name", async () => {
      vi.spyOn(api, "getMe").mockResolvedValue({ sub: "pessoa-1", nome: null });

      renderShellAt("/");

      await waitFor(() => expect(screen.getAllByRole("link", SIGN_OUT).length).toBeGreaterThan(0));
      expect(screen.getByText("Equipe")).toBeInTheDocument();
    });

    it("offers no sign out outside the login, where that address does not exist", async () => {
      const getMe = vi.spyOn(api, "getMe").mockResolvedValue(null);

      renderShellAt("/");

      await waitFor(() => expect(getMe).toHaveBeenCalled());
      expect(screen.getByText("Equipe")).toBeInTheDocument();
      expect(screen.queryByRole("link", SIGN_OUT)).toBeNull();
    });
  });
});
