import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageBubble } from "../../src/components/MessageBubble";
import type { ConversationMessage } from "../../src/types";

const MESSAGE: ConversationMessage = {
  id: "m1",
  direction: "entrada",
  tipo: "texto",
  conteudo: "Bom dia!",
  idioma: "pt",
  created_at: "2026-09-28T09:14:00Z",
};

function renderBubble(overrides: Partial<ConversationMessage> = {}) {
  render(
    <ul>
      <MessageBubble message={{ ...MESSAGE, ...overrides }} />
    </ul>
  );
}

describe("MessageBubble", () => {
  it("shows the text and the time of the message", () => {
    renderBubble();

    expect(screen.getByText("Bom dia!")).toBeInTheDocument();
    const time = screen.getByText(/^\d{2}:\d{2}$/);
    expect(time).toHaveAttribute("datetime", "2026-09-28T09:14:00Z");
  });

  it("aligns the assistant's messages to the right with the action color", () => {
    renderBubble({ direction: "saida" });

    expect(screen.getByText("Bom dia!").parentElement).toHaveClass("bg-action");
    expect(screen.getByRole("listitem")).toHaveClass("ml-auto");
  });

  it("keeps the tourist's messages on the left over the surface color", () => {
    renderBubble();

    expect(screen.getByText("Bom dia!").parentElement).toHaveClass("bg-surface");
    expect(screen.getByRole("listitem")).not.toHaveClass("ml-auto");
    // Alinhado ao início: sem isso o balão esticaria até a largura máxima, mesmo com texto curto.
    expect(screen.getByRole("listitem")).toHaveClass("items-start");
  });

  it("marks transcribed audio", () => {
    renderBubble({ tipo: "audio_transcrito" });

    expect(screen.getByText("transcrito de áudio")).toBeInTheDocument();
  });

  it("does not mark plain text as transcribed", () => {
    renderBubble();

    expect(screen.queryByText("transcrito de áudio")).toBeNull();
  });
});
