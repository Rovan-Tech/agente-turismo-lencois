import type { Theme } from "../lib/theme";
import type { Me } from "../types";
import { Brand } from "./Brand";
import { NavLinks } from "./NavLinks";
import { ThemeToggle } from "./ThemeToggle";
import { MobileSignOut } from "./UserMenu";

/** Cabeçalho do celular: sem a barra lateral, a marca e a navegação ficam no topo. */
export function MobileHeader({
  me,
  theme,
  onToggleTheme,
}: {
  me: Me | null;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  return (
    <header className="border-b border-subtle bg-surface px-4 py-3 md:hidden">
      <div className="flex items-center justify-between">
        <Brand />
        <div className="flex items-center gap-4">
          <MobileSignOut me={me} />
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </div>
      <NavLinks className="mt-3 flex gap-2" />
    </header>
  );
}
