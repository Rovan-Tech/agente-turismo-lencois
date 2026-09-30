import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ConversationsPage } from "../../src/pages/ConversationsPage";
import * as api from "../../src/lib/api";
import type { ConversationSummary } from "../../src/types";

function summary(overrides: Partial<ConversationSummary>): ConversationSummary {
  return {
    id: "abc123",
    whatsapp_phone: "5598999998888",
    status: "aberta",
    idioma_detectado: "pt",
    updated_at: "2026-09-25T12:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  render(
    <MemoryRouter>
      <ConversationsPage />
    </MemoryRouter>
  );
}

describe("ConversationsPage", () => {
  it.each([
    ["there are no conversations", []],
    ["the API call fails", null],
  ])("shows an empty state when %s", async (_case, response) => {
    vi.spyOn(api, "listConversations").mockResolvedValue(response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Nenhuma conversa encontrada.")).toBeInTheDocument();
    });
  });

  it("lists conversations with their status", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([summary({ status: "precisa_atencao" })]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("5598999998888")).toBeInTheDocument();
    });
    expect(screen.getByText("Precisa de atenção")).toBeInTheDocument();
  });

  it("de-emphasizes resolved conversations in the list", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([
      summary({ id: "a", whatsapp_phone: "5598900000001", status: "precisa_atencao" }),
      summary({ id: "b", whatsapp_phone: "5598900000002", status: "resolvida" }),
    ]);

    renderPage();

    expect(await screen.findByText("5598900000001")).toHaveClass("text-primary");
    expect(screen.getByText("5598900000002")).toHaveClass("text-muted");
  });
});
