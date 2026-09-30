import { languageCode } from "../lib/conversations";

/** Círculo com a sigla do idioma detectado (PT, EN, ES); "—" quando ainda não se sabe. */
export function LanguageAvatar({ idioma }: { idioma: string | null }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent-subtle"
    >
      {languageCode(idioma)}
    </span>
  );
}
