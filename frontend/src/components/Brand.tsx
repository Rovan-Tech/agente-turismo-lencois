/** Marca do painel: selo circular com o arco da lagoa e o nome da agência. */
export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-action text-on-action">
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M5 15c2-5 5-7 7-7s5 2 7 7" />
        </svg>
      </span>
      <div className="leading-tight">
        <p className="font-display text-sm font-bold text-primary">Vento Branco Expedições</p>
        <p className="text-xs text-muted">Painel do agente</p>
      </div>
    </div>
  );
}
