import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ConversationDetailPage } from "./pages/ConversationDetailPage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { ToursPage } from "./pages/ToursPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<ConversationsPage />} />
          <Route path="/conversas/:id" element={<ConversationDetailPage />} />
          <Route path="/passeios" element={<ToursPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
