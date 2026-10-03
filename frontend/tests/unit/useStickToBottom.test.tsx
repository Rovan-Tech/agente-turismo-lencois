import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MessageList } from "../../src/components/MessageList";
import { useStickToBottom } from "../../src/lib/useStickToBottom";
import type { ConversationMessage } from "../../src/types";

const GEOMETRY = { scrollHeight: 1000, clientHeight: 200 };
const END = 800;
const maxTop = () => GEOMETRY.scrollHeight - GEOMETRY.clientHeight;

/** O jsdom não faz layout: a lista ganha altura e rolagem simuladas. */
function useFakeGeometry(log: HTMLElement) {
  Object.defineProperty(log, "scrollHeight", {
    configurable: true,
    get: () => GEOMETRY.scrollHeight,
  });
  Object.defineProperty(log, "clientHeight", {
    configurable: true,
    get: () => GEOMETRY.clientHeight,
  });
  let top = 0;
  Object.defineProperty(log, "scrollTop", {
    configurable: true,
    get: () => top,
    set: (value: number) => {
      top = Math.min(Math.max(value, 0), maxTop());
    },
  });
}

function Harness({ resetKey, changeKey }: Readonly<{ resetKey: string; changeKey: string }>) {
  const scroll = useStickToBottom(resetKey, changeKey);
  return (
    <>
      <div ref={scroll.ref} onScroll={scroll.onScroll} data-testid="log" />
      <button type="button" onClick={scroll.pin}>
        pin
      </button>
    </>
  );
}

/** Renderiza e dá geometria à lista antes do primeiro efeito de rolagem. */
function renderHarness(resetKey = "a", changeKey = "m1") {
  const view = render(<Harness resetKey={resetKey} changeKey={changeKey} />);
  const log = screen.getByTestId("log");
  useFakeGeometry(log);
  // A conversa abre no fim, como o navegador deixa depois do primeiro efeito de rolagem.
  scrollTo(log, END);
  return {
    log,
    rerender: (reset: string, change: string) =>
      view.rerender(<Harness resetKey={reset} changeKey={change} />),
  };
}

function scrollTo(log: HTMLElement, top: number) {
  log.scrollTop = top;
  fireEvent.scroll(log);
}

/** O jsdom não tem ResizeObserver: o stub guarda o callback para o teste disparar a mudança de tamanho. */
function stubResizeObserver() {
  const notify = { current: (): void => {} };
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        notify.current = callback;
      }
      observe() {}
      disconnect() {}
    }
  );
  return notify;
}

describe("useStickToBottom", () => {
  afterEach(() => {
    GEOMETRY.scrollHeight = 1000;
    vi.unstubAllGlobals();
  });

  it.each([
    ["follows new content while the reader is at the end", [], END],
    ["stays where it is when the reader went up to read older content", [100], 100],
    ["follows again once the reader comes back to the end", [100, END - 10], END],
  ])("%s", (_name, scrolls, expected) => {
    const { log, rerender } = renderHarness();
    for (const top of scrolls) scrollTo(log, top);

    act(() => rerender("a", "m2"));

    expect(log.scrollTop).toBe(expected);
  });

  it("does not take a scroll the browser made on its own, without going up, as leaving the end", () => {
    const { log, rerender } = renderHarness();
    // O conteúdo cresceu e o navegador reposicionou sozinho (âncora): a posição nunca subiu.
    GEOMETRY.scrollHeight = 1300;
    fireEvent.scroll(log);

    act(() => rerender("a", "m2"));

    expect(log.scrollTop).toBe(maxTop());
  });

  it("goes back to the end when another conversation opens", () => {
    const { log, rerender } = renderHarness();
    scrollTo(log, 100);

    act(() => rerender("b", "n1"));

    expect(log.scrollTop).toBe(END);
  });

  it("pin brings the reader to the end and keeps following", () => {
    const { log, rerender } = renderHarness();
    scrollTo(log, 100);

    fireEvent.click(screen.getByRole("button", { name: "pin" }));
    expect(log.scrollTop).toBe(END);

    act(() => rerender("a", "m2"));
    expect(log.scrollTop).toBe(END);
  });

  it("keeps the end when the list is resized and the reader was at the end", () => {
    const notify = stubResizeObserver();
    const { log } = renderHarness();
    scrollTo(log, 0);
    scrollTo(log, END);
    log.scrollTop = 0;

    act(() => notify.current());

    expect(log.scrollTop).toBe(END);
  });

  it("does not move a resized list whose reader went up", () => {
    const notify = stubResizeObserver();
    const { log } = renderHarness();
    scrollTo(log, 100);

    act(() => notify.current());

    expect(log.scrollTop).toBe(100);
  });
});

describe("MessageList", () => {
  const MESSAGES: ConversationMessage[] = [
    {
      id: "m1",
      direction: "entrada",
      tipo: "texto",
      conteudo: "Olá!",
      idioma: "pt",
      autor: "turista",
      created_at: "2026-09-28T09:14:00Z",
    },
  ];

  it("is a keyboard-focusable log with the messages inside", () => {
    const scroll = { ref: vi.fn(), onScroll: vi.fn(), pin: vi.fn() };

    render(<MessageList messages={MESSAGES} scroll={scroll} />);

    const log = screen.getByRole("log", { name: "Mensagens da conversa" });
    expect(log).toHaveAttribute("tabindex", "0");
    expect(log).toHaveTextContent("Olá!");
    fireEvent.scroll(log);
    expect(scroll.onScroll).toHaveBeenCalled();
  });
});
