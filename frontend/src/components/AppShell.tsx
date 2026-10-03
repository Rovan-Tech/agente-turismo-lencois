import { Outlet, useMatch } from "react-router-dom";

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
  // A conversa aberta não pode crescer com as mensagens: a casca ocupa só a altura da janela e a
  // página rola a lista por dentro. As demais telas seguem crescendo com o conteúdo.
  const fitsViewport = useMatch("/conversas/:id") !== null;
  return (
    <div className={`flex flex-col bg-page ${fitsViewport ? "h-dvh" : "min-h-screen"}`}>
      {IS_DEMO && <DemoBanner />}
      <div className={fitsViewport ? "flex min-h-0 flex-1" : "md:flex md:flex-1"}>
        <Sidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <MobileHeader me={me} theme={theme} onToggleTheme={toggleTheme} />
          <Topbar now={new Date()} me={me} theme={theme} onToggleTheme={toggleTheme} />
          <Outlet />
        </div>
      </div>
    </div>
  );
}
