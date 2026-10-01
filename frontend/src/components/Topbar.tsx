import type { Theme } from "../lib/theme";
import { formatLongDate } from "../lib/time";
import type { Me } from "../types";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";

/** Faixa do topo (desktop): data de hoje, o tema e quem está logado, com o botão para sair. */
export function Topbar({
  now,
  me,
  theme,
  onToggleTheme,
}: {
  now: Date;
  me: Me | null;
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
      <UserMenu me={me} />
    </header>
  );
}
