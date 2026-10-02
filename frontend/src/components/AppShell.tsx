import { Outlet } from "react-router-dom";

import { useMe } from "../features/handoff/useMe";
import { useTheme } from "../lib/useTheme";
import { MobileHeader } from "./MobileHeader";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/** Casca do painel: barra lateral + topo em volta da página da rota atual. */
export function AppShell() {
  const [theme, toggleTheme] = useTheme();
  const me = useMe();
  return (
    <div className="min-h-screen bg-page md:flex">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader me={me} theme={theme} onToggleTheme={toggleTheme} />
        <Topbar now={new Date()} me={me} theme={theme} onToggleTheme={toggleTheme} />
        <Outlet />
      </div>
    </div>
  );
}
