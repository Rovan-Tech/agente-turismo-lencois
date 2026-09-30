import { Outlet } from "react-router-dom";

import { useTheme } from "../lib/useTheme";
import { MobileHeader } from "./MobileHeader";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/** Casca do painel: barra lateral + topo em volta da página da rota atual. */
export function AppShell() {
  const [theme, toggleTheme] = useTheme();
  return (
    <div className="min-h-screen bg-page md:flex">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader theme={theme} onToggleTheme={toggleTheme} />
        <Topbar now={new Date()} theme={theme} onToggleTheme={toggleTheme} />
        <Outlet />
      </div>
    </div>
  );
}
