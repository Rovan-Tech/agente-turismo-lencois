import { initialsOf, languageCode } from "../lib/conversations";

/**
 * Círculo do avatar da conversa: as iniciais do nome do cliente, quando o WhatsApp o informou;
 * sem nome, a sigla do idioma detectado (PT, EN, ES) ou "—" se ainda não se sabe.
 */
export function LanguageAvatar({
  idioma,
  nome = null,
}: Readonly<{ idioma: string | null; nome?: string | null }>) {
  return (
    <span
      aria-hidden="true"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent-subtle"
    >
      {initialsOf(nome) ?? languageCode(idioma)}
    </span>
  );
}
