import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ConversationsPage } from "../../src/pages/ConversationsPage";
import * as api from "../../src/lib/api";

describe("ConversationsPage", () => {
  it("shows an empty state when there are no conversations", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ConversationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Nenhuma conversa encontrada.")).toBeInTheDocument();
    });
  });

  it("lists conversations with their status", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([
      {
        id: "abc123",
        whatsapp_phone: "5598999998888",
        status: "precisa_atencao",
        idioma_detectado: "pt",
        updated_at: "2026-09-25T12:00:00Z",
      },
    ]);

    render(
      <MemoryRouter>
        <ConversationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("5598999998888")).toBeInTheDocument();
    });
    expect(screen.getByText("Precisa de atenção")).toBeInTheDocument();
  });

  it("falls back to an empty list when the API call fails", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue(null);

    render(
      <MemoryRouter>
        <ConversationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Nenhuma conversa encontrada.")).toBeInTheDocument();
    });
  });
});
