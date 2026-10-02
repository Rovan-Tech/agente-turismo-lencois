import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReplyComposer } from "../../src/features/handoff/ReplyComposer";

const FIELD = { name: "Resposta ao turista" };
const SEND = { name: "Enviar" };

function renderComposer(
  onSend: (text: string) => Promise<boolean>,
  props: { blockedReason?: string | null; error?: string | null } = {}
) {
  render(
    <ReplyComposer
      blockedReason={props.blockedReason ?? null}
      error={props.error ?? null}
      onSend={onSend}
    />
  );
}

function type(text: string) {
  fireEvent.change(screen.getByRole("textbox", FIELD), { target: { value: text } });
}

describe("ReplyComposer", () => {
  it("sends the trimmed text and clears the field once the server accepts it", async () => {
    const onSend = vi.fn().mockResolvedValue(true);
    renderComposer(onSend);

    type("  Claro, posso ajudar!  ");
    fireEvent.click(screen.getByRole("button", SEND));

    await waitFor(() => expect(screen.getByRole("textbox", FIELD)).toHaveValue(""));
    expect(onSend).toHaveBeenCalledWith("Claro, posso ajudar!");
  });

  it("keeps the text when the server refuses, so the person does not retype it", async () => {
    const onSend = vi.fn().mockResolvedValue(false);
    renderComposer(onSend, { error: "Não foi possível enviar a mensagem pelo WhatsApp." });

    type("Olá");
    fireEvent.click(screen.getByRole("button", SEND));

    await waitFor(() => expect(onSend).toHaveBeenCalled());
    expect(screen.getByRole("textbox", FIELD)).toHaveValue("Olá");
    expect(screen.getByRole("alert")).toHaveTextContent("pelo WhatsApp");
  });

  it.each(["", "   "])("does not send an empty message (%j)", (text) => {
    const onSend = vi.fn();
    renderComposer(onSend);

    type(text);

    expect(screen.getByRole("button", SEND)).toBeDisabled();
    expect(onSend).not.toHaveBeenCalled();
  });

  it("sends with Ctrl+Enter, and Enter alone only breaks the line", async () => {
    const onSend = vi.fn().mockResolvedValue(true);
    renderComposer(onSend);
    type("Oi");
    const field = screen.getByRole("textbox", FIELD);

    fireEvent.keyDown(field, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(field, { key: "Enter", ctrlKey: true });

    await waitFor(() => expect(onSend).toHaveBeenCalledWith("Oi"));
  });

  it("blocks the field and explains why when the 24 hour window is closed", () => {
    renderComposer(vi.fn(), { blockedReason: "Mais de 24 horas sem resposta do turista." });

    expect(screen.getByRole("textbox", FIELD)).toBeDisabled();
    expect(screen.getByRole("button", SEND)).toBeDisabled();
    expect(screen.getByText("Mais de 24 horas sem resposta do turista.")).toBeInTheDocument();
  });

  it("counts the characters against the WhatsApp limit and stops typing at it", () => {
    renderComposer(vi.fn());

    type("abc");

    expect(screen.getByText("3/4096")).toBeInTheDocument();
    expect(screen.getByRole("textbox", FIELD)).toHaveAttribute("maxlength", "4096");
  });

  it("does not send twice while the first request is in flight", async () => {
    const onSend = vi.fn().mockReturnValue(new Promise(() => {}));
    renderComposer(onSend);
    type("Oi");

    fireEvent.click(screen.getByRole("button", SEND));
    await waitFor(() => expect(screen.getByRole("button", { name: "Enviando…" })).toBeDisabled());
    fireEvent.keyDown(screen.getByRole("textbox", FIELD), { key: "Enter", ctrlKey: true });

    expect(onSend).toHaveBeenCalledTimes(1);
  });
});
