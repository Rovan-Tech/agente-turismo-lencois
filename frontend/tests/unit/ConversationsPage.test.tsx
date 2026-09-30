import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import { ConversationsPage } from "../../src/pages/ConversationsPage";
import type { ConversationSummary } from "../../src/types";
import { summary } from "./fixtures";

function renderPage(conversations: ConversationSummary[] | null) {
  vi.spyOn(api, "listConversations").mockResolvedValue(conversations);
  render(
    <MemoryRouter>
      <ConversationsPage />
    </MemoryRouter>
  );
}

const MIXED = [
  summary({
    id: "a",
    whatsapp_phone: "5598900000001",
    status: "precisa_atencao",
    idioma_detectado: "en",
    ultima_mensagem: {
      conteudo: "Is the Lagoa Azul tour wheelchair accessible?",
      tipo: "texto",
      direction: "entrada",
      created_at: new Date().toISOString(),
    },
  }),
  summary({ id: "b", whatsapp_phone: "5598900000002", status: "resolvida" }),
  summary({ id: "c", whatsapp_phone: "5598900000003", status: "aberta", idioma_detectado: "es" }),
];

describe("ConversationsPage", () => {
  it.each([
    ["there are no conversations", []],
    ["the API call fails", null],
  ])("shows an empty state when %s", async (_case, response) => {
    renderPage(response);

    expect(await screen.findByText("Nenhuma conversa encontrada.")).toBeInTheDocument();
  });

  it("lists each conversation with formatted phone, preview, language and status", async () => {
    renderPage(MIXED);

    const row = (await screen.findByText("+55 98 90000-0001")).closest("a");
    expect(row).not.toBeNull();
    const withinRow = within(row as HTMLElement);
    expect(
      withinRow.getByText("Is the Lagoa Azul tour wheelchair accessible?")
    ).toBeInTheDocument();
    expect(withinRow.getByText("EN")).toBeInTheDocument();
    expect(withinRow.getByText("Precisa de atenção")).toBeInTheDocument();
    expect(withinRow.getByText("agora")).toBeInTheDocument();
    expect(row).toHaveAttribute("href", "/conversas/a");
  });

  it("highlights the ones that need attention and mutes the resolved ones", async () => {
    renderPage(MIXED);

    const attention = (await screen.findByText("+55 98 90000-0001")).closest("a");
    expect(attention).toHaveClass("border-l-attention");
    expect(screen.getByText("+55 98 90000-0002").closest("p")).toHaveClass("text-muted");
    expect(screen.getByText("+55 98 90000-0003").closest("p")).toHaveClass("text-primary");
  });

  it("shows how many conversations each tab holds", async () => {
    renderPage(MIXED);

    await screen.findByText("+55 98 90000-0001");
    expect(screen.getByRole("button", { name: "Todas 3" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abertas 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Precisam de atenção 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resolvidas 1" })).toBeInTheDocument();
  });

  it("filters the list when a status tab is chosen", async () => {
    renderPage(MIXED);
    await screen.findByText("+55 98 90000-0001");

    fireEvent.click(screen.getByRole("button", { name: "Resolvidas 1" }));

    expect(screen.getByRole("button", { name: "Resolvidas 1" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByText("+55 98 90000-0002")).toBeInTheDocument();
    expect(screen.queryByText("+55 98 90000-0001")).toBeNull();
  });

  it("searches by phone or by the last message and says when nothing matches", async () => {
    renderPage(MIXED);
    await screen.findByText("+55 98 90000-0001");
    const search = screen.getByRole("searchbox", { name: "Buscar por telefone ou mensagem" });

    fireEvent.change(search, { target: { value: "wheelchair" } });
    expect(screen.getByText("+55 98 90000-0001")).toBeInTheDocument();
    expect(screen.queryByText("+55 98 90000-0003")).toBeNull();

    fireEvent.change(search, { target: { value: "90000-0003" } });
    expect(screen.getByText("+55 98 90000-0003")).toBeInTheDocument();

    fireEvent.change(search, { target: { value: "zzz" } });
    await waitFor(() => {
      expect(
        screen.getByText("Nenhuma conversa corresponde ao filtro ou à busca.")
      ).toBeInTheDocument();
    });
  });

  it("tells screen readers when the last message came from a transcribed audio", async () => {
    renderPage([
      summary({
        ultima_mensagem: {
          conteudo: "quero um passeio",
          tipo: "audio_transcrito",
          direction: "entrada",
          created_at: new Date().toISOString(),
        },
      }),
    ]);

    expect(await screen.findByRole("img", { name: "áudio transcrito" })).toBeInTheDocument();
  });

  it("says so when a conversation has no messages yet", async () => {
    renderPage([summary({ ultima_mensagem: null })]);

    expect(await screen.findByText("Sem mensagens")).toBeInTheDocument();
  });
});
