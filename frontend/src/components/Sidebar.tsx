import { Brand } from "./Brand";
import { NavLinks } from "./NavLinks";

/** Barra lateral do desktop: marca, navegação e o indicativo do assistente de IA. */
export function Sidebar() {
  return (
    <aside
      aria-label="Barra lateral"
      className="hidden w-sidebar shrink-0 flex-col border-r border-subtle bg-page px-3 py-5 md:flex"
    >
      <div className="px-3">
        <Brand />
      </div>
      <NavLinks className="mt-6 flex flex-col gap-1" />
      <div className="mt-auto flex items-start gap-2 rounded-md border border-subtle bg-surface px-3 py-3 text-xs text-secondary">
        <span aria-hidden="true" className="mt-1 h-2 w-2 shrink-0 rounded-full bg-online" />
        <p>Assistente de IA respondendo agora</p>
      </div>
    </aside>
  );
}
