import type { Theme } from "../lib/theme";
import { ThemeToggle } from "./ThemeToggle";
import { UserIcon } from "./icons";
import { formatLongDate } from "../lib/time";

/** Faixa do topo (desktop): data de hoje e o usuário da equipe. */
export function Topbar({
  now,
  theme,
  onToggleTheme,
}: {
  now: Date;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  return (
    <header className="hidden items-center justify-end gap-4 border-b border-subtle bg-surface px-6 py-3 text-sm md:flex">
      <time dateTime={now.toLocaleDateString("sv-SE")} className="text-secondary">
        {formatLongDate(now)}
      </time>
      <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      <span aria-hidden="true" className="h-5 w-px bg-neutral-subtle" />
      <span className="flex items-center gap-2 font-medium text-primary">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-subtle text-neutral-subtle">
          <UserIcon />
        </span>
        Equipe
      </span>
    </header>
  );
}
