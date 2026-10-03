import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { TranslateToggle } from "../../src/components/TranslateToggle";
import { TRANSLATE_FAILURE } from "./fixtures";

describe("TranslateToggle", () => {
  it("fetches and shows the translation, then hides it on a second click", async () => {
    vi.spyOn(api, "translateText").mockResolvedValue({ ok: true, data: "Good morning!" });

    render(<TranslateToggle texto="Bom dia!" />);
    fireEvent.click(screen.getByRole("button", { name: /Traduzir/ }));

    expect(await screen.findByText("Good morning!")).toBeInTheDocument();
    expect(api.translateText).toHaveBeenCalledWith("Bom dia!", "pt");

    fireEvent.click(screen.getByRole("button", { name: "Ocultar tradução" }));
    expect(screen.queryByText("Good morning!")).toBeNull();
  });

  it("shows an error when the translation fails, without crashing", async () => {
    vi.spyOn(api, "translateText").mockResolvedValue(TRANSLATE_FAILURE);

    render(<TranslateToggle texto="Bom dia!" />);
    fireEvent.click(screen.getByRole("button", { name: /Traduzir/ }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível traduzir agora.");
    });
  });
});
