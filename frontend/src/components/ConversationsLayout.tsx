import { Outlet, useMatch } from "react-router-dom";

import { ConversationsPage } from "../pages/ConversationsPage";

/**
 * Casca da seção Conversas: lista à esquerda, conversa selecionada à direita (`/conversas/:id`
 * casado por `<Outlet/>`), lado a lado a partir de `lg`. Abaixo disso mostra só uma coluna de
 * cada vez — a lista em "/", a conversa em "/conversas/:id" — igual ao comportamento de sempre.
 */
export function ConversationsLayout() {
  const hasOpenConversation = useMatch("/conversas/:id") !== null;

  return (
    <main
      className={`flex min-w-0 flex-1 flex-col lg:grid lg:grid-cols-2 lg:divide-x lg:divide-subtle ${
        hasOpenConversation ? "min-h-0" : ""
      }`}
    >
      <div
        className={`${hasOpenConversation ? "hidden lg:flex lg:min-h-0 lg:flex-col lg:overflow-y-auto" : "flex flex-1 flex-col"}`}
      >
        <ConversationsPage />
      </div>
      <div
        className={
          hasOpenConversation
            ? "flex min-h-0 flex-1 flex-col"
            : "hidden lg:flex lg:min-h-0 lg:flex-1 lg:flex-col"
        }
      >
        <Outlet />
      </div>
    </main>
  );
}
