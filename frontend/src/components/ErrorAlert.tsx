/** Mensagem de erro anunciada por leitores de tela (a causa vem do servidor ou é a padrão). */
export function ErrorAlert({ message }: Readonly<{ message: string }>) {
  return (
    <p role="alert" className="text-sm text-status-error">
      {message}
    </p>
  );
}
