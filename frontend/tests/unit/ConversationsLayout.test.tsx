import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ConversationEmptyState } from "../../src/components/ConversationEmptyState";
import { ConversationsLayout } from "../../src/components/ConversationsLayout";
import * as api from "../../src/lib/api";
import { ConversationDetailPage } from "../../src/pages/ConversationDetailPage";
import { SAMPLE_CONVERSATION, summary } from "./fixtures";

const ROUTES = (
  <Route element={<ConversationsLayout />}>
    <Route path="/" element={<ConversationEmptyState />} />
    <Route path="/conversas/:id" element={<ConversationDetailPage />} />
  </Route>
);

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>{ROUTES}</Routes>
    </MemoryRouter>
  );
}

describe("ConversationsLayout", () => {
  it("shows the list and the empty state at the root route", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([summary({ id: "a" })]);
    renderAt("/");

    expect(await screen.findByText("+55 98 99999-8888")).toBeInTheDocument();
    expect(screen.getByText("Selecione uma conversa")).toBeInTheDocument();
  });

  it("shows the list alongside the open conversation at /conversas/:id", async () => {
    vi.spyOn(api, "listConversations").mockResolvedValue([summary({ id: SAMPLE_CONVERSATION.id })]);
    vi.spyOn(api, "getConversation").mockResolvedValue(SAMPLE_CONVERSATION);
    renderAt(`/conversas/${SAMPLE_CONVERSATION.id}`);

    // A lista continua montada (ela só fica escondida por CSS abaixo de `lg`, que o jsdom não
    // aplica), ao lado do conteúdo da conversa aberta.
    expect(await screen.findAllByText("+55 98 99999-8888")).toHaveLength(2);
    expect(screen.getByText("quero um passeio")).toBeInTheDocument();
  });
});
