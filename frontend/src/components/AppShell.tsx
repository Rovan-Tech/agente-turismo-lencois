import { Outlet } from "react-router-dom";

import { useMe } from "../features/handoff/useMe";
import { IS_DEMO } from "../lib/demo";
import { useTheme } from "../lib/useTheme";
import { DemoBanner } from "./DemoBanner";
import { MobileHeader } from "./MobileHeader";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/** Casca do painel: barra lateral + topo em volta da página da rota atual. */
export function AppShell() {
  const [theme, toggleTheme] = useTheme();
  const me = useMe();
  return (
    <div className="flex min-h-screen flex-col bg-page">
      {IS_DEMO && <DemoBanner />}
      <div className="md:flex md:flex-1">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <MobileHeader me={me} theme={theme} onToggleTheme={toggleTheme} />
          <Topbar now={new Date()} me={me} theme={theme} onToggleTheme={toggleTheme} />
          <Outlet />
        </div>
      </div>
    </div>
  );
}
