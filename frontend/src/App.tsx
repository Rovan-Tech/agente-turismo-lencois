import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ConversationDetailPage } from "./pages/ConversationDetailPage";
import { ConversationsPage } from "./pages/ConversationsPage";

export function App() {
  return (
    <BrowserRouter>
      <header className="border-b border-grafite/10 bg-lagoa">
        <div className="mx-auto max-w-3xl px-4 py-4">
          <p className="font-display text-lg font-semibold text-white">
            Agência de Turismo em Lençóis
          </p>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<ConversationsPage />} />
        <Route path="/conversas/:id" element={<ConversationDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
