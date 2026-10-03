import type { LanguageFilter, LanguageFilterOption } from "../lib/conversations";
import { FilterTabs, type FilterTabItem } from "./FilterTabs";

/** Abas de filtro por idioma; nascem dos idiomas detectados nos dados (ver `languageFilterOptions`). */
export function LanguageFilterTabs({
  active,
  options,
  onChange,
}: Readonly<{
  active: LanguageFilter;
  options: readonly LanguageFilterOption[];
  onChange: (filter: LanguageFilter) => void;
}>) {
  // "Todos" + nenhum ou um só idioma: filtrar não ajudaria em nada.
  if (options.length <= 2) return null;

  const items: FilterTabItem<LanguageFilter>[] = options.map(({ value, code, label, count }) => ({
    value,
    selected: value === active,
    count,
    content: (
      <>
        {code && (
          <span className="rounded bg-accent-subtle px-1.5 text-xs font-bold text-accent-subtle">
            {code}
          </span>
        )}
        {label}
      </>
    ),
  }));

  return (
    <FilterTabs
      ariaLabel="Filtrar por idioma"
      legend={<legend className="mr-1 text-xs font-semibold text-secondary">Idioma</legend>}
      items={items}
      pill={false}
      onChange={onChange}
    />
  );
}
