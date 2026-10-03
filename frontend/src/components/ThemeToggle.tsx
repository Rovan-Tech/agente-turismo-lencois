import type { Theme } from "../lib/theme";
import { MoonIcon, SunIcon } from "./icons";

/** Botão que alterna entre o modo claro e o escuro; o rótulo diz o que ele vai fazer. */
export function ThemeToggle({ theme, onToggle }: Readonly<{ theme: Theme; onToggle: () => void }>) {
  const dark = theme === "dark";
  const label = dark ? "Usar modo claro" : "Usar modo escuro";
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={label}
      title={label}
      className="flex h-8 w-8 items-center justify-center rounded-full border border-subtle text-secondary hover:bg-subtle"
    >
      {dark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
