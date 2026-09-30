import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ConversationDetailPage } from "../../src/pages/ConversationDetailPage";

function renderAt(id: string) {
  render(
    <MemoryRouter initialEntries={[`/conversas/${id}`]}>
      <Routes>
        <Route path="/conversas/:id" element={<ConversationDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ConversationDetailPage", () => {
  it("shows a not found message when the conversation does not exist", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue(null);

    renderAt("nao-existe");

    await waitFor(() => {
      expect(screen.getByText("Conversa não encontrada.")).toBeInTheDocument();
    });
  });

  it("shows the conversation messages, marking transcribed audio", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue({
      id: "abc123",
      whatsapp_phone: "5598999998888",
      status: "aberta",
      idioma_detectado: "pt",
      updated_at: "2026-09-25T12:01:00Z",
      messages: [
        {
          id: "m1",
          direction: "entrada",
          tipo: "audio_transcrito",
          conteudo: "quero um passeio",
          idioma: "pt",
          created_at: "2026-09-25T12:00:00Z",
        },
        {
          id: "m2",
          direction: "saida",
          tipo: "texto",
          conteudo: "Recomendo o bugre!",
          idioma: "pt",
          created_at: "2026-09-25T12:01:00Z",
        },
      ],
    });

    renderAt("abc123");

    await waitFor(() => {
      expect(screen.getByText("quero um passeio")).toBeInTheDocument();
    });
    expect(screen.getByText("5598999998888")).toBeInTheDocument();
    expect(screen.getByText("transcrito de áudio")).toBeInTheDocument();
    expect(screen.getByText("Recomendo o bugre!")).toBeInTheDocument();
  });
});
