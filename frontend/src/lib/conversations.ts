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
  query: string
): ConversationSummary[] {
  const text = normalize(query.trim());
  const digits = PHONE_QUERY.test(query.trim()) ? digitsOf(query) : "";
  return conversations.filter((conversation) => {
    if (filter !== "todas" && conversation.status !== filter) return false;
    if (!text) return true;
    const matchesPhone = digits !== "" && digitsOf(conversation.whatsapp_phone).includes(digits);
    const preview = normalize(conversation.ultima_mensagem?.conteudo ?? "");
    return matchesPhone || preview.includes(text);
  });
}

/**
 * Iniciais para o avatar: a primeira letra (ou dígito) da primeira e da última palavra do nome,
 * "Mariana Souza" -> "MS", "Zé" -> "Z". Palavra sem letra (emoji, símbolo) é ignorada; sem nenhuma
 * letra, `null` (o avatar volta à sigla do idioma).
 */
export function initialsOf(name: string | null): string | null {
  if (!name) return null;
  const letters = name
    .trim()
    .split(/\s+/)
    .map((word) => Array.from(word).find((char) => /[\p{L}\p{N}]/u.test(char)))
    .filter((char): char is string => char !== undefined);
  if (letters.length === 0) return null;
  const picked = letters.length === 1 ? letters[0] : letters[0] + letters[letters.length - 1];
  return picked.toLocaleUpperCase();
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
