import type { ConversationStatus, ConversationSummary } from "../types";

export type StatusFilter = "todas" | ConversationStatus;

export const STATUS_FILTERS: ReadonlyArray<{ value: StatusFilter; label: string }> = [
  { value: "todas", label: "Todas" },
  { value: "aberta", label: "Abertas" },
  { value: "precisa_atencao", label: "Precisam de atenção" },
  { value: "resolvida", label: "Resolvidas" },
];

const LANGUAGE_NAMES: Record<string, string> = {
  pt: "português",
  en: "inglês",
  es: "espanhol",
};

/** Minúsculas e sem acentos, para a busca não depender de como o turista digitou. */
function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

function digitsOf(text: string): string {
  return text.replace(/\D/g, "");
}

/** Uma consulta "de telefone" só tem dígitos e a pontuação de número; "3 anos" não é telefone. */
const PHONE_QUERY = /^[\d\s()+-]+$/;

export function countByFilter(
  conversations: readonly ConversationSummary[]
): Record<StatusFilter, number> {
  const counts: Record<StatusFilter, number> = {
    todas: conversations.length,
    aberta: 0,
    precisa_atencao: 0,
    resolvida: 0,
  };
  for (const conversation of conversations) counts[conversation.status] += 1;
  return counts;
}

/** Filtra por aba de status e por busca (telefone, só dígitos, ou prévia da última mensagem). */
export function filterConversations(
  conversations: readonly ConversationSummary[],
  filter: StatusFilter,
  query: string,
  language: LanguageFilter = "todos"
): ConversationSummary[] {
  const text = normalize(query.trim());
  const digits = PHONE_QUERY.test(query.trim()) ? digitsOf(query) : "";
  return conversations.filter((conversation) => {
    if (filter !== "todas" && conversation.status !== filter) return false;
    if (language !== "todos" && languageCode(conversation.idioma_detectado) !== language) {
      return false;
    }
    if (!text) return true;
    const matchesPhone = digits !== "" && digitsOf(conversation.whatsapp_phone).includes(digits);
    const preview = normalize(conversation.ultima_mensagem?.conteudo ?? "");
    return matchesPhone || preview.includes(text);
  });
}

/** "todos" ou um código de duas letras ("PT", "EN"…); nasce dos idiomas vistos nos dados. */
export type LanguageFilter = "todos" | string;

export interface LanguageFilterOption {
  value: LanguageFilter;
  code: string | null;
  label: string;
  count: number;
}

/**
 * Opções do filtro de idioma: "Todos os idiomas" seguido de cada idioma detectado, do mais para o
 * menos frequente. Um idioma novo nos dados aparece sozinho, sem precisar alterar código (mesma
 * regra do desenho do redesign: "o filtro nasce dos idiomas que a IA detectou").
 */
export function languageFilterOptions(
  conversations: readonly ConversationSummary[]
): LanguageFilterOption[] {
  const counts = new Map<string, number>();
  for (const conversation of conversations) {
    const code = languageCode(conversation.idioma_detectado);
    if (code === "—") continue;
    counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  const byCount = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  return [
    { value: "todos", code: null, label: "Todos os idiomas", count: conversations.length },
    ...byCount.map(([code, count]) => ({
      value: code,
      code,
      label: languageName(code.toLowerCase()) ?? code,
      count,
    })),
  ];
}

/** "PT", "EN", "ES"; "—" quando o idioma ainda não foi detectado. */
export function languageCode(idioma: string | null): string {
  return idioma ? idioma.slice(0, 2).toUpperCase() : "—";
}

export function languageName(idioma: string | null): string | null {
  return idioma ? (LANGUAGE_NAMES[idioma.slice(0, 2).toLowerCase()] ?? idioma) : null;
}

/**
 * "5598991842201" -> "+55 98 99184-2201". A máscara é a do Brasil e só vale para números que
 * começam com 55; os de outros países (turistas) ficam como "+<número>" para não parecerem
 * brasileiros com o agrupamento errado. Texto que não é número volta como veio.
 */
export function formatPhone(raw: string): string {
  if (!/^\d+$/.test(raw)) return raw;
  const match = /^(55)(\d{2})(\d{4,5})(\d{4})$/.exec(raw);
  return match ? `+${match[1]} ${match[2]} ${match[3]}-${match[4]}` : `+${raw}`;
}
