import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ConversationDetailPage } from "../../src/pages/ConversationDetailPage";
import type { ConversationDetail, ConversationStatus } from "../../src/types";
import { HANDLED_CONVERSATION, ME, SAMPLE_CONVERSATION, SAMPLE_SUGGESTED_TOUR } from "./fixtures";

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
  beforeEach(() => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
  });

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

describe("ConversationDetailPage: taking over and answering", () => {
  const REPLY_FIELD = { name: "Resposta ao turista" };
  const TAKE_OVER = { name: "Assumir conversa" };

  beforeEach(() => {
    vi.spyOn(api, "getMe").mockResolvedValue(ME);
  });

  /** O servidor devolve a conversa sem atendente e, depois de assumir, com a pessoa atendendo. */
  function serveConversation(...versions: ConversationDetail[]) {
    const getConversation = vi.spyOn(api, "getConversation");
    versions.forEach((version, index) => {
      if (index === versions.length - 1) getConversation.mockResolvedValue(version);
      else getConversation.mockResolvedValueOnce(version);
    });
    return getConversation;
  }

  it("takes over the conversation, rereads it and shows the reply field", async () => {
    const takeOver = vi.spyOn(api, "takeOverConversation").mockResolvedValue({
      ok: true,
      data: HANDLED_CONVERSATION,
    });
    serveConversation(SAMPLE_CONVERSATION, HANDLED_CONVERSATION);
    renderAt("abc123");
    expect(screen.queryByRole("textbox", REPLY_FIELD)).toBeNull();

    fireEvent.click(await screen.findByRole("button", TAKE_OVER));

    expect(await screen.findByRole("textbox", REPLY_FIELD)).toBeInTheDocument();
    expect(takeOver).toHaveBeenCalledWith("abc123");
    expect(screen.getByText("Você está atendendo")).toBeInTheDocument();
  });

  it("shows why the server refused to take over and stays with the AI", async () => {
    vi.spyOn(api, "takeOverConversation").mockResolvedValue({
      ok: false,
      status: 409,
      message: "A conversa já está com Bia. Peça para devolver à IA.",
    });
    serveConversation(SAMPLE_CONVERSATION);
    renderAt("abc123");

    fireEvent.click(await screen.findByRole("button", TAKE_OVER));

    expect(await screen.findByRole("alert")).toHaveTextContent("já está com Bia");
    expect(screen.queryByRole("textbox", REPLY_FIELD)).toBeNull();
    expect(screen.getByRole("button", TAKE_OVER)).toBeEnabled();
  });

  it("gives the conversation back to the AI and hides the reply field", async () => {
    const giveBack = vi
      .spyOn(api, "giveBackConversation")
      .mockResolvedValue({ ok: true, data: SAMPLE_CONVERSATION });
    serveConversation(HANDLED_CONVERSATION, SAMPLE_CONVERSATION);
    renderAt("abc123");

    fireEvent.click(await screen.findByRole("button", { name: "Devolver para a IA" }));

    expect(await screen.findByRole("button", TAKE_OVER)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", REPLY_FIELD)).toBeNull();
    expect(giveBack).toHaveBeenCalledWith("abc123");
  });

  it("only shows the reply field to the person who is attending", async () => {
    serveConversation({ ...HANDLED_CONVERSATION, atendente_sub: "outra", atendente_nome: "Bia" });

    renderAt("abc123");

    expect(await screen.findByText("Atendendo: Bia")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", REPLY_FIELD)).toBeNull();
  });

  it("sends the reply and adds it to the conversation without rereading", async () => {
    const reply = {
      id: "m2",
      direction: "saida",
      tipo: "texto",
      conteudo: "Claro, posso ajudar!",
      idioma: "pt",
      autor: "atendente",
      created_at: new Date().toISOString(),
    } as const;
    const send = vi
      .spyOn(api, "sendConversationReply")
      .mockResolvedValue({ ok: true, data: reply });
    const recent = {
      ...HANDLED_CONVERSATION,
      messages: [{ ...HANDLED_CONVERSATION.messages[0], created_at: new Date().toISOString() }],
    };
    const getConversation = serveConversation(recent);
    renderAt("abc123");

    fireEvent.change(await screen.findByRole("textbox", REPLY_FIELD), {
      target: { value: "Claro, posso ajudar!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("Claro, posso ajudar!", { selector: "p" })).toBeInTheDocument();
    expect(send).toHaveBeenCalledWith("abc123", "Claro, posso ajudar!", expect.any(String));
    expect(getConversation).toHaveBeenCalledTimes(1);
  });

  it("reuses the send id when the same text is retried after a failure", async () => {
    const send = vi
      .spyOn(api, "sendConversationReply")
      .mockResolvedValue({ ok: false, status: 502, message: "Não foi possível enviar." });
    serveConversation({
      ...HANDLED_CONVERSATION,
      messages: [{ ...HANDLED_CONVERSATION.messages[0], created_at: new Date().toISOString() }],
    });
    renderAt("abc123");
    fireEvent.change(await screen.findByRole("textbox", REPLY_FIELD), { target: { value: "Oi" } });

    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    await screen.findByText("Não foi possível enviar.");
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));

    expect(send.mock.calls[1][2]).toBe(send.mock.calls[0][2]);
  });

  it("blocks the reply field when the tourist's last message is older than 24 hours", async () => {
    serveConversation(HANDLED_CONVERSATION);

    renderAt("abc123");

    expect(await screen.findByRole("textbox", REPLY_FIELD)).toBeDisabled();
    expect(screen.getByText(/mais de 24 horas/)).toBeInTheDocument();
  });

  describe("while a person is attending", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it("rereads the conversation every 15 seconds so new tourist messages show up", async () => {
      const arrived = {
        ...HANDLED_CONVERSATION,
        messages: [
          ...HANDLED_CONVERSATION.messages,
          { ...HANDLED_CONVERSATION.messages[0], id: "m7", conteudo: "e o preço?" },
        ],
      };
      const getConversation = serveConversation(HANDLED_CONVERSATION, arrived);
      renderAt("abc123");
      await screen.findByText("quero um passeio");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(15_000);
      });

      expect(await screen.findByText("e o preço?")).toBeInTheDocument();
      expect(getConversation).toHaveBeenCalledTimes(2);
    });

    /** Abre a conversa e deixa passar `ms` de relógio simulado. */
    async function openAndWait(first: ConversationDetail, ms: number) {
      const getConversation = serveConversation(first);
      renderAt("abc123");
      await screen.findByText("quero um passeio");
      return {
        getConversation,
        wait: () =>
          act(async () => {
            await vi.advanceTimersByTimeAsync(ms);
          }),
      };
    }

    it("does not reread while the AI is answering", async () => {
      const { getConversation, wait } = await openAndWait(SAMPLE_CONVERSATION, 60_000);

      await wait();

      expect(getConversation).toHaveBeenCalledTimes(1);
    });

    it("keeps what is on screen when a reread fails", async () => {
      const { getConversation, wait } = await openAndWait(HANDLED_CONVERSATION, 15_000);
      getConversation.mockResolvedValue(null);

      await wait();

      expect(screen.getByText("quero um passeio")).toBeInTheDocument();
      expect(screen.queryByText("Conversa não encontrada.")).toBeNull();
    });
  });
});
