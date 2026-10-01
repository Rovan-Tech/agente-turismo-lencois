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
  autor: "turista",
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

  it("shows markup in a message as plain text, never as elements", () => {
    const markup = '<img src=x onerror="alert(1)"><script>alert(2)</script>';

    renderBubble({ conteudo: markup });

    expect(screen.getByText(markup)).toBeInTheDocument();
    expect(document.querySelector("img, script")).toBeNull();
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

  it.each([
    ["ia", "Assistente de IA"],
    ["atendente", "Equipe"],
  ] as const)("says who wrote a message from the %s", (autor, label) => {
    renderBubble({ direction: "saida", autor });

    expect(screen.getByText(new RegExp(`^${label} ·`))).toBeInTheDocument();
  });

  it("does not label the tourist's own messages", () => {
    renderBubble({ autor: "turista" });

    expect(screen.queryByText(/·/)).toBeNull();
  });
});
