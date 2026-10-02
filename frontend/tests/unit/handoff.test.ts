import { describe, expect, it } from "vitest";

import { isReplyWindowOpen, newClientMessageId } from "../../src/lib/handoff";
import type { ConversationMessage } from "../../src/types";

const NOW = new Date("2026-10-01T12:00:00Z");

function message(autor: ConversationMessage["autor"], createdAt: string): ConversationMessage {
  return {
    id: `${autor}-${createdAt}`,
    direction: autor === "turista" ? "entrada" : "saida",
    tipo: "texto",
    conteudo: "oi",
    idioma: null,
    autor,
    created_at: createdAt,
  };
}

describe("isReplyWindowOpen", () => {
  it.each([
    ["a minute ago", "2026-10-01T11:59:00Z", true],
    ["exactly 24 hours ago", "2026-09-30T12:00:00Z", true],
    ["24 hours and a minute ago", "2026-09-30T11:59:00Z", false],
  ])("for a tourist message %s", (_when, createdAt, expected) => {
    expect(isReplyWindowOpen([message("turista", createdAt)], NOW)).toBe(expected);
  });

  it("uses the most recent tourist message", () => {
    const messages = [
      message("turista", "2026-09-29T08:00:00Z"),
      message("turista", "2026-10-01T10:00:00Z"),
    ];

    expect(isReplyWindowOpen(messages, NOW)).toBe(true);
  });

  it("does not count what the assistant or the team wrote", () => {
    const messages = [
      message("turista", "2026-09-29T08:00:00Z"),
      message("ia", "2026-10-01T11:00:00Z"),
      message("atendente", "2026-10-01T11:30:00Z"),
    ];

    expect(isReplyWindowOpen(messages, NOW)).toBe(false);
  });

  it("is closed when the tourist never wrote", () => {
    expect(isReplyWindowOpen([], NOW)).toBe(false);
  });
});

describe("newClientMessageId", () => {
  it("returns an id the server accepts, different every time", () => {
    const [first, second] = [newClientMessageId(), newClientMessageId()];

    expect(first).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
    expect(first).not.toBe(second);
  });
});
