export function ActiveBadge({ ativo }: Readonly<{ ativo: boolean }>) {
  return (
    <output
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
        ativo ? "bg-accent-subtle text-accent-subtle" : "bg-neutral-subtle text-neutral-subtle"
      }`}
    >
      {ativo ? "Ativo" : "Inativo"}
    </output>
  );
}
