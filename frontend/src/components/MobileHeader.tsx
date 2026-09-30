import type { Theme } from "../lib/theme";
import { Brand } from "./Brand";
import { NavLinks } from "./NavLinks";
import { ThemeToggle } from "./ThemeToggle";

/** Cabeçalho do celular: sem a barra lateral, a marca e a navegação ficam no topo. */
export function MobileHeader({
  theme,
  onToggleTheme,
}: {
  theme: Theme;
  onToggleTheme: () => void;
}) {
  return (
    <header className="border-b border-subtle bg-surface px-4 py-3 md:hidden">
      <div className="flex items-center justify-between">
        <Brand />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
      <NavLinks className="mt-3 flex gap-2" />
    </header>
  );
}
