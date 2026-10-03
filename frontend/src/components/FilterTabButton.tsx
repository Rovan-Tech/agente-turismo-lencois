import type { ReactNode } from "react";

/** Botão das abas de filtro (status, idioma): estado selecionado em `bg-action`, com selo de contagem. */
export function FilterTabButton({
  selected,
  onClick,
  count,
  pill = true,
  children,
}: Readonly<{
  selected: boolean;
  onClick: () => void;
  count: number;
  /** `true` = cápsula (status); `false` = cantos moderados (idioma, com selo de código antes do texto). */
  pill?: boolean;
  children: ReactNode;
}>) {
  const shape = pill ? "rounded-full px-4" : "rounded-md px-3";
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`flex items-center gap-2 border py-2 text-sm font-semibold ${shape} ${
        selected
          ? "border-transparent bg-action text-on-action"
          : "border-subtle bg-surface text-secondary hover:bg-subtle"
      }`}
    >
      {children}
      <span className="rounded-full bg-neutral-subtle px-2 text-xs text-neutral-subtle">
        {count}
      </span>
    </button>
  );
}
