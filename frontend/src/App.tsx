import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ConversationEmptyState } from "./components/ConversationEmptyState";
import { ConversationsLayout } from "./components/ConversationsLayout";
import { AnalisesPage } from "./pages/AnalisesPage";
import { ConversationDetailPage } from "./pages/ConversationDetailPage";
import { TourBookingPage } from "./pages/TourBookingPage";
import { ToursPage } from "./pages/ToursPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route element={<ConversationsLayout />}>
            <Route path="/" element={<ConversationEmptyState />} />
            <Route path="/conversas/:id" element={<ConversationDetailPage />} />
          </Route>
          <Route path="/passeios" element={<ToursPage />} />
          <Route path="/passeios/:id" element={<TourBookingPage />} />
          <Route path="/analises" element={<AnalisesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
