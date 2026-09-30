import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ConversationDetailPage } from "../../src/pages/ConversationDetailPage";
import type { ConversationDetail, ConversationStatus } from "../../src/types";
import { SAMPLE_CONVERSATION, SAMPLE_SUGGESTED_TOUR } from "./fixtures";

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

/** Abre uma conversa que já vem resolvida do servidor. */
function renderResolved() {
  vi.spyOn(api, "getConversation").mockResolvedValue({
    ...SAMPLE_CONVERSATION,
    status: "resolvida",
  });
  renderAt("abc123");
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
    expect(screen.getByText("+55 98 99999-8888")).toBeInTheDocument();
    expect(screen.getByText("transcrito de áudio")).toBeInTheDocument();
    expect(screen.getByText("Recomendo o bugre!")).toBeInTheDocument();
  });

  it("shows the tour the assistant suggested in the side panel", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue({
      ...SAMPLE_CONVERSATION,
      passeio_sugerido: SAMPLE_SUGGESTED_TOUR,
    });

    renderAt("abc123");

    const card = await screen.findByRole("region", { name: "Passeio sugerido pela IA" });
    expect(within(card).getByText("Mirante Vila Acessível")).toBeInTheDocument();
    expect(within(card).getByText("R$ 120")).toBeInTheDocument();
  });

  it("says no tour was suggested yet when the conversation has none", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue(SAMPLE_CONVERSATION);

    renderAt("abc123");

    expect(
      await screen.findByText("A IA ainda não sugeriu um passeio nesta conversa.")
    ).toBeInTheDocument();
  });

  it("shows since when the customer talks to the agency and the detected language", async () => {
    vi.spyOn(api, "getConversation").mockResolvedValue({
      ...SAMPLE_CONVERSATION,
      idioma_detectado: "en",
      created_at: "2026-09-22T12:00:00Z",
    });

    renderAt("abc123");

    expect(await screen.findByText("Cliente desde 22 de setembro · inglês")).toBeInTheDocument();
    expect(screen.getByText("EN")).toBeInTheDocument();
  });

  it("marks the conversation as resolved from the status control too", async () => {
    const resolve = vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
      ok: true,
      data: { ...SAMPLE_CONVERSATION, status: "resolvida" },
    });
    vi.spyOn(api, "getConversation").mockResolvedValue(SAMPLE_CONVERSATION);

    renderAt("abc123");
    const resolvida = () => screen.getByRole("button", { name: "Resolvida" });
    fireEvent.click(await screen.findByRole("button", { name: "Resolvida" }));

    await waitFor(() => {
      expect(resolvida()).toHaveAttribute("aria-pressed", "true");
    });
    expect(resolve).toHaveBeenCalledWith("abc123", "resolvida");
  });

  it("reopens a resolved conversation from the status control", async () => {
    const update = vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
      ok: true,
      data: { ...SAMPLE_CONVERSATION, status: "aberta" },
    });
    renderResolved();
    fireEvent.click(await screen.findByRole("button", { name: "Aberta" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Aberta");
    });
    expect(update).toHaveBeenCalledWith("abc123", "aberta");
    expect(screen.getByRole("button", { name: "Marcar como resolvida" })).toBeInTheDocument();
  });

  it("does not steal the focus when the status is changed from the control", async () => {
    vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
      ok: true,
      data: { ...SAMPLE_CONVERSATION, status: "precisa_atencao" },
    });
    vi.spyOn(api, "getConversation").mockResolvedValue(SAMPLE_CONVERSATION);

    renderAt("abc123");
    const option = await screen.findByRole("button", { name: "Precisa de atenção" });
    option.focus();
    fireEvent.click(option);

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Precisa de atenção");
    });
    expect(option).toHaveFocus();
  });

  it.each<ConversationStatus>(["aberta", "precisa_atencao"])(
    "marks a %s conversation as resolved and updates the badge without reloading",
    async (status) => {
      const resolve = vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
        ok: true,
        data: { ...SAMPLE_CONVERSATION, status: "resolvida" },
      });

      const getConversation = await openAndClickResolve({ ...SAMPLE_CONVERSATION, status });

      await waitFor(() => {
        expect(screen.getByRole("status")).toHaveTextContent("Resolvida");
      });
      expect(resolve).toHaveBeenCalledWith("abc123", "resolvida");
      // Sem recarregar: a tela atualiza o estado local em vez de buscar a conversa de novo.
      expect(getConversation).toHaveBeenCalledTimes(1);
      // O botão saiu do DOM: o foco vai para o título e o usuário de teclado não se perde.
      expect(screen.getByRole("heading", { name: "+55 98 99999-8888" })).toHaveFocus();
      expect(screen.queryByRole("button", RESOLVE_BUTTON)).toBeNull();
      expect(screen.getByText("quero um passeio")).toBeInTheDocument();
    }
  );

  it("ignores a late response that belongs to another conversation", async () => {
    vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
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
    renderResolved();

    await screen.findByText("+55 98 99999-8888");
    expect(screen.queryByRole("button", RESOLVE_BUTTON)).toBeNull();
  });

  it("keeps the status and shows an error when the API rejects the change", async () => {
    vi.spyOn(api, "updateConversationStatus").mockResolvedValue({
      ok: false,
      status: 500,
      message: "falha",
    });

    await openAndClickResolve();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível alterar o status. Tente novamente."
    );
    expect(screen.getByRole("status")).toHaveTextContent("Aberta");
    expect(screen.getByRole("button", RESOLVE_BUTTON)).toBeEnabled();
  });

  it("disables the button while the request is in flight", async () => {
    vi.spyOn(api, "updateConversationStatus").mockReturnValue(new Promise(() => {}));

    await openAndClickResolve();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
    });
  });
});
