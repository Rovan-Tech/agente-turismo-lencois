import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { HandoffSection } from "../../src/features/handoff/HandoffSection";
import type { ConversationHeader, Me } from "../../src/types";
import { HANDLED_CONVERSATION, ME, SAMPLE_CONVERSATION } from "./fixtures";

const NO_MESSAGES: ConversationHeader = SAMPLE_CONVERSATION;

function renderSection(
  conversation: ConversationHeader,
  me: Me | null = ME,
  extra: { busy?: boolean; error?: string | null } = {}
) {
  const onTakeOver = vi.fn();
  const onGiveBack = vi.fn();
  render(
    <HandoffSection
      conversation={conversation}
      me={me}
      busy={extra.busy ?? false}
      error={extra.error ?? null}
      onTakeOver={onTakeOver}
      onGiveBack={onGiveBack}
    />
  );
  return { onTakeOver, onGiveBack };
}

describe("HandoffSection", () => {
  it("offers to take over a conversation the AI answers and shows the name the tourist will see", () => {
    const { onTakeOver } = renderSection(NO_MESSAGES);

    expect(screen.getByText("O assistente de IA responde esta conversa.")).toBeInTheDocument();
    expect(screen.getByText("O turista verá o aviso com o seu nome: Ana.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Assumir conversa" }));
    expect(onTakeOver).toHaveBeenCalledOnce();
  });

  it.each([
    [
      "is not known yet",
      null,
      "O turista será avisado de que uma pessoa da nossa equipe está falando.",
    ],
    [
      "has no usable first name",
      { sub: "pessoa-123", nome: null },
      "O turista será avisado de que uma pessoa da equipe está falando, sem nome (o seu login não tem um primeiro nome utilizável).",
    ],
  ])("says the notice goes without a name when the login %s", (_case, me, expected) => {
    renderSection(NO_MESSAGES, me);

    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it("tells the person they are the one attending and lets them give it back", () => {
    const { onGiveBack } = renderSection(HANDLED_CONVERSATION);

    expect(screen.getByText("Você está atendendo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Assumir conversa" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Devolver para a IA" }));
    expect(onGiveBack).toHaveBeenCalledOnce();
  });

  it("shows who else is attending, with the option to free a forgotten conversation", () => {
    renderSection({ ...HANDLED_CONVERSATION, atendente_sub: "outra", atendente_nome: "Bia" });

    expect(screen.getByText("Atendendo: Bia")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Devolver para a IA" })).toBeEnabled();
  });

  it("blocks taking over a conversation another person attends and says why", () => {
    const { onTakeOver } = renderSection({
      ...HANDLED_CONVERSATION,
      atendente_sub: "outra",
      atendente_nome: "Bia",
    });

    const button = screen.getByRole("button", { name: "Assumir conversa" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(/Você não pode assumir: a conversa já está com Bia/);
    fireEvent.click(button);
    expect(onTakeOver).not.toHaveBeenCalled();
  });

  it("does not show the blocked take over to the person who is attending", () => {
    renderSection(HANDLED_CONVERSATION);

    expect(screen.queryByRole("button", { name: "Assumir conversa" })).toBeNull();
    expect(screen.queryByText(/Você não pode assumir/)).toBeNull();
  });

  it("names nobody when the holder has no first name", () => {
    renderSection({ ...HANDLED_CONVERSATION, atendente_sub: "outra", atendente_nome: null });

    expect(screen.getByText("Atendendo: outra pessoa da equipe")).toBeInTheDocument();
    expect(screen.getByText(/já está com outra pessoa da equipe/)).toBeInTheDocument();
  });

  it("does not offer to take over a resolved conversation", () => {
    renderSection({ ...SAMPLE_CONVERSATION, status: "resolvida" });

    expect(screen.queryByRole("button", { name: "Assumir conversa" })).toBeNull();
    expect(screen.getByText("Reabra a conversa para assumir.")).toBeInTheDocument();
  });

  it("disables the button while the request is in flight and shows the server's reason", () => {
    renderSection(NO_MESSAGES, ME, { busy: true, error: "A conversa já está com Bia." });

    expect(screen.getByRole("button", { name: "Assumindo…" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("A conversa já está com Bia.");
  });
});
