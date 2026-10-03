import { describe, expect, it } from "vitest";

import {
  countByFilter,
  filterConversations,
  formatPhone,
  languageCode,
  languageFilterOptions,
  languageName,
} from "../../src/lib/conversations";
import type { ConversationSummary } from "../../src/types";
import { summary } from "./fixtures";

const LIST: ConversationSummary[] = [
  summary({
    id: "a",
    whatsapp_phone: "5598991842201",
    status: "aberta",
    ultima_mensagem: message("Quais passeios vocês têm pra quem tem medo de altura?"),
  }),
  summary({
    id: "b",
    whatsapp_phone: "5598982127743",
    status: "precisa_atencao",
    ultima_mensagem: message("Is the Lagoa Azul tour wheelchair accessible?"),
  }),
  summary({ id: "c", whatsapp_phone: "5598977881190", status: "resolvida" }),
  summary({
    id: "d",
    whatsapp_phone: "5598900000000",
    status: "aberta",
    ultima_mensagem: message("Vocês têm passeio pra criança de 3 anos?"),
  }),
];

function message(conteudo: string): ConversationSummary["ultima_mensagem"] {
  return { conteudo, tipo: "texto", direction: "entrada", created_at: "2026-09-28T12:00:00Z" };
}

describe("countByFilter", () => {
  it("counts each status and the total", () => {
    expect(countByFilter(LIST)).toEqual({
      todas: 4,
      aberta: 2,
      precisa_atencao: 1,
      resolvida: 1,
    });
  });
});

describe("filterConversations", () => {
  const ids = (filter: Parameters<typeof filterConversations>[1], query = "") =>
    filterConversations(LIST, filter, query).map((c) => c.id);

  it("keeps everything for 'todas' without a query", () => {
    expect(ids("todas")).toEqual(["a", "b", "c", "d"]);
  });

  it("filters by status tab", () => {
    expect(ids("precisa_atencao")).toEqual(["b"]);
  });

  it.each([
    ["formatted phone digits", "98 98212", ["b"]],
    ["with country code and symbols", "+55 98 99184-2201", ["a"]],
    ["message text ignoring accents and case", "VOCES TEM", ["a", "d"]],
    ["english message", "wheelchair", ["b"]],
    ["no match", "zzz", []],
    ["words containing a digit only in the message, not as a phone", "3 anos", ["d"]],
  ])("searches by %s", (_case, query, expected) => {
    expect(ids("todas", query)).toEqual(expected);
  });

  it("combines the status tab with the search", () => {
    expect(ids("aberta", "wheelchair")).toEqual([]);
    expect(ids("precisa_atencao", "wheelchair")).toEqual(["b"]);
  });

  it("ignores a query made only of spaces", () => {
    expect(ids("todas", "   ")).toEqual(["a", "b", "c", "d"]);
  });

  it("filters by language", () => {
    const list = [
      summary({ id: "a", idioma_detectado: "pt" }),
      summary({ id: "b", idioma_detectado: "en" }),
    ];
    expect(filterConversations(list, "todas", "", "EN").map((c) => c.id)).toEqual(["b"]);
  });

  it("combines status, language and search", () => {
    const list = [
      summary({
        id: "a",
        status: "aberta",
        idioma_detectado: "en",
        ultima_mensagem: message("hello"),
      }),
      summary({
        id: "b",
        status: "aberta",
        idioma_detectado: "pt",
        ultima_mensagem: message("hello"),
      }),
    ];
    expect(filterConversations(list, "aberta", "hello", "EN").map((c) => c.id)).toEqual(["a"]);
  });
});

describe("languageFilterOptions", () => {
  it("lists 'todos' plus each detected language, most frequent first", () => {
    const list = [
      summary({ id: "a", idioma_detectado: "pt" }),
      summary({ id: "b", idioma_detectado: "en" }),
      summary({ id: "c", idioma_detectado: "pt" }),
      summary({ id: "d", idioma_detectado: null }),
    ];
    expect(languageFilterOptions(list)).toEqual([
      { value: "todos", code: null, label: "Todos os idiomas", count: 4 },
      { value: "PT", code: "PT", label: "português", count: 2 },
      { value: "EN", code: "EN", label: "inglês", count: 1 },
    ]);
  });

  it("returns only 'todos' when nothing has a detected language", () => {
    expect(languageFilterOptions([summary({ idioma_detectado: null })])).toEqual([
      { value: "todos", code: null, label: "Todos os idiomas", count: 1 },
    ]);
  });
});

describe("language and phone helpers", () => {
  it.each([
    ["pt", "PT"],
    ["en-US", "EN"],
    [null, "—"],
  ])("languageCode(%s) -> %s", (input, expected) => {
    expect(languageCode(input)).toBe(expected);
  });

  it.each([
    ["en", "inglês"],
    ["es", "espanhol"],
    ["fr", "fr"],
    [null, null],
  ])("languageName(%s) -> %s", (input, expected) => {
    expect(languageName(input)).toBe(expected);
  });

  it.each([
    ["5598991842201", "+55 98 99184-2201"],
    ["559891842201", "+55 98 9184-2201"],
    ["447911123456", "+447911123456"],
    ["5491123456789", "+5491123456789"],
    ["abc", "abc"],
  ])("formatPhone(%s) -> %s", (input, expected) => {
    expect(formatPhone(input)).toBe(expected);
  });
});
