import { ChatIcon } from "./icons";

/** Preenche a coluna da conversa quando nenhuma está selecionada (só aparece em telas largas). */
export function ConversationEmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-secondary">
      <ChatIcon className="h-8 w-8" />
      <p className="font-display text-lg font-semibold text-primary">Selecione uma conversa</p>
      <p className="max-w-xs text-sm">Escolha uma conversa na lista para ver as mensagens aqui.</p>
    </div>
  );
}
