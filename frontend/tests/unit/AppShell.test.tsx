import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../../src/components/AppShell";

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
    expect(screen.getAllByText("Lençóis Tour").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Painel do agente").length).toBeGreaterThan(0);
    expect(screen.getByText("Assistente de IA respondendo agora")).toBeInTheDocument();
    expect(screen.getByText("Equipe")).toBeInTheDocument();
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
});
