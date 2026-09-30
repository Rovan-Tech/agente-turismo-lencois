import { SearchIcon } from "./icons";

const LABEL = "Buscar por telefone ou mensagem";

export function SearchBox({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex w-full items-center gap-2 rounded-md border border-subtle bg-surface px-3 py-2 text-sm text-muted sm:w-search focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus">
      <SearchIcon />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={LABEL}
        aria-label={LABEL}
        className="w-full bg-transparent text-primary placeholder:text-muted focus:outline-none"
      />
    </label>
  );
}
