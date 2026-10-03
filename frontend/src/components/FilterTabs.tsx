import type { ReactNode } from "react";

import { FilterTabButton } from "./FilterTabButton";

export interface FilterTabItem<T extends string> {
  readonly value: T;
  readonly selected: boolean;
  readonly count: number;
  readonly content: ReactNode;
}

/** Um `<fieldset>` de abas de filtro (status, idioma…), cada uma com selo de contagem. */
export function FilterTabs<T extends string>({
  ariaLabel,
  legend,
  items,
  pill = true,
  onChange,
}: Readonly<{
  ariaLabel: string;
  legend?: ReactNode;
  items: readonly FilterTabItem<T>[];
  /** `true` (padrão) = cápsula; `false` = cantos moderados. */
  pill?: boolean;
  onChange: (value: T) => void;
}>) {
  return (
    <fieldset aria-label={ariaLabel} className="min-w-0 flex flex-wrap items-center gap-2">
      {legend}
      {items.map((item) => (
        <FilterTabButton
          key={item.value}
          selected={item.selected}
          onClick={() => onChange(item.value)}
          count={item.count}
          pill={pill}
        >
          {item.content}
        </FilterTabButton>
      ))}
    </fieldset>
  );
}
