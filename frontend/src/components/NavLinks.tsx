import { Link, useLocation } from "react-router-dom";

import { ChatIcon, CompassIcon } from "./icons";

const NAV_ITEMS = [
  {
    to: "/",
    label: "Conversas",
    Icon: ChatIcon,
    isActive: (path: string) => path === "/" || path.startsWith("/conversas"),
  },
  {
    to: "/passeios",
    label: "Passeios",
    Icon: CompassIcon,
    isActive: (path: string) => path.startsWith("/passeios"),
  },
];

/** Links de navegação do painel; o item da seção atual recebe `aria-current="page"`. */
export function NavLinks({ className }: { className: string }) {
  const { pathname } = useLocation();
  return (
    <nav aria-label="Principal" className={className}>
      {NAV_ITEMS.map(({ to, label, Icon, isActive }) => {
        const active = isActive(pathname);
        return (
          <Link
            key={to}
            to={to}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
              active
                ? "bg-accent-subtle font-semibold text-accent-subtle"
                : "font-medium text-secondary hover:bg-subtle"
            }`}
          >
            <Icon />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
