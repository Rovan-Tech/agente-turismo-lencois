import { STATUS_FILTERS, type StatusFilter } from "../lib/conversations";
import { FilterTabs, type FilterTabItem } from "./FilterTabs";

/** Abas de filtro por status; cada uma mostra quantas conversas tem. */
export function StatusFilterTabs({
  active,
  counts,
  onChange,
}: Readonly<{
  active: StatusFilter;
  counts: Record<StatusFilter, number>;
  onChange: (filter: StatusFilter) => void;
}>) {
  const items: FilterTabItem<StatusFilter>[] = STATUS_FILTERS.map(({ value, label }) => ({
    value,
    selected: value === active,
    count: counts[value],
    content: label,
  }));
  return <FilterTabs ariaLabel="Filtrar por status" items={items} onChange={onChange} />;
}
