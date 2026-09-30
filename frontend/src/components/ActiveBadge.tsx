export function ActiveBadge({ ativo }: { ativo: boolean }) {
  return (
    <span
      role="status"
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
        ativo ? "bg-accent-subtle text-accent-subtle" : "bg-neutral-subtle text-neutral-subtle"
      }`}
    >
      {ativo ? "Ativo" : "Inativo"}
    </span>
  );
}
