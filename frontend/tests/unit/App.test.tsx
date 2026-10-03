import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "../../src/App";
import * as api from "../../src/lib/api";

async function expectHeading(name: string) {
  await waitFor(() => {
    expect(screen.getByRole("heading", { name })).toBeInTheDocument();
  });
}

describe("App routing", () => {
  it("shows the conversations page at the root route", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([]);
    window.history.pushState({}, "", "/");

    render(<App />);

    await expectHeading("Conversas");
  });

  it("shows the tours page at /passeios", async () => {
    vi.spyOn(api, "listTours").mockResolvedValue([]);
    window.history.pushState({}, "", "/passeios");

    render(<App />);

    await expectHeading("Passeios");
  });

  it("navigates to the tours page via the header link", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([]);
    vi.spyOn(api, "listTours").mockResolvedValue([]);
    window.history.pushState({}, "", "/");

    render(<App />);
    await screen.findByRole("heading", { name: "Conversas" });

    within(screen.getByRole("complementary", { name: "Barra lateral" }))
      .getByRole("link", { name: "Passeios" })
      .click();

    await expectHeading("Passeios");
  });
});
