import { BrowserRouter, Link, Route, Routes } from "react-router-dom";

import { ConversationDetailPage } from "./pages/ConversationDetailPage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { ToursPage } from "./pages/ToursPage";

export function App() {
  return (
    <BrowserRouter>
      <header className="border-b border-subtle bg-header">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <p className="font-display text-lg font-semibold text-on-header">
            Agência de Turismo em Lençóis
          </p>
          <nav className="flex gap-4 text-sm font-medium text-on-header">
            <Link to="/">Conversas</Link>
            <Link to="/passeios">Passeios</Link>
          </nav>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<ConversationsPage />} />
        <Route path="/conversas/:id" element={<ConversationDetailPage />} />
        <Route path="/passeios" element={<ToursPage />} />
      </Routes>
    </BrowserRouter>
  );
}
