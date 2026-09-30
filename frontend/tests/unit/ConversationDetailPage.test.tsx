import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ConversationDetailPage } from "../../src/pages/ConversationDetailPage";
import type { ConversationDetail, ConversationStatus } from "../../src/types";
import { SAMPLE_CONVERSATION } from "./fixtures";

const RESOLVE_BUTTON = { name: "Marcar como resolvida" };

function renderAt(id: string) {
  render(
    <MemoryRouter initialEntries={[`/conversas/${id}`]}>
      <Routes>
        <Route path="/conversas/:id" element={<ConversationDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

/** Abre a conversa e clica em "Marcar como resolvida" assim que o botão aparece. */
async function openAndClickResolve(conversation: ConversationDetail = SAMPLE_CONVERSATION) {
  const getConversation = vi.spyOn(api, "getConversation").mockResolvedValue(conversation);
  renderAt(conversation.id);
  fireEvent.click(await screen.findByRole("button", RESOLVE_BUTTON));
  return getConversation;
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
    const [firstMessage] = SAMPLE_CONVERSATION.messages;
    vi.spyOn(api, "getConversation").mockResolvedValue({
      ...SAMPLE_CONVERSATION,
      messages: [
        { ...firstMessage, tipo: "audio_transcrito" },
        { ...firstMessage, id: "m2", direction: "saida", conteudo: "Recomendo o bugre!" },
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

  it.each<ConversationStatus>(["aberta", "precisa_atencao"])(
    "marks a %s conversation as resolved and updates the badge without reloading",
    async (status) => {
      const resolve = vi.spyOn(api, "resolveConversation").mockResolvedValue({
        ok: true,
        data: { ...SAMPLE_CONVERSATION, status: "resolvida" },
      });

      const getConversation = await openAndClickResolve({ ...SAMPLE_CONVERSATION, status });

      await waitFor(() => {
        expect(screen.getByRole("status")).toHaveTextContent("Resolvida");
      });
      expect(resolve).toHaveBeenCalledWith("abc123");
      // Sem recarregar: a tela atualiza o estado local em vez de buscar a conversa de novo.
      expect(getConversation).toHaveBeenCalledTimes(1);
      // O botão saiu do DOM: o foco vai para o título e o usuário de teclado não se perde.
      expect(screen.getByRole("heading", { name: "5598999998888" })).toHaveFocus();
      expect(screen.queryByRole("button", RESOLVE_BUTTON)).toBeNull();
      expect(screen.getByText("quero um passeio")).toBeInTheDocument();
    }
  );

  it("ignores a late response that belongs to another conversation", async () => {
    vi.spyOn(api, "resolveConversation").mockResolvedValue({
      ok: true,
      data: { ...SAMPLE_CONVERSATION, id: "outra", status: "resolvida" },
    });

    await openAndClickResolve();

    await waitFor(() => {
      expect(screen.getByRole("button", RESOLVE_BUTTON)).toBeEnabled();
    });
    expect(screen.getByRole("status")).toHaveTextContent("Aberta");
  });

  it("does not offer the action for a conversation that is already resolved", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue({
      ...SAMPLE_CONVERSATION,
      status: "resolvida",
    });

    renderAt("abc123");

    await screen.findByText("5598999998888");
    expect(screen.queryByRole("button", RESOLVE_BUTTON)).toBeNull();
  });

  it("keeps the status and shows an error when the API rejects the change", async () => {
    vi.spyOn(api, "resolveConversation").mockResolvedValue({
      ok: false,
      status: 500,
      message: "falha",
    });

    await openAndClickResolve();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível marcar como resolvida. Tente novamente."
    );
    expect(screen.getByRole("status")).toHaveTextContent("Aberta");
    expect(screen.getByRole("button", RESOLVE_BUTTON)).toBeEnabled();
  });

  it("disables the button while the request is in flight", async () => {
    vi.spyOn(api, "resolveConversation").mockReturnValue(new Promise(() => {}));

    await openAndClickResolve();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Marcando…" })).toBeDisabled();
    });
  });
});
