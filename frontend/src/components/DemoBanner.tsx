import { DEMO_WHATSAPP } from "../lib/demo";

/** Faixa fixa da demonstração: deixa claro que os dados são fictícios e leva ao contato real. */
export function DemoBanner() {
  return (
    <div
      role="note"
      className="sticky top-0 z-sticky flex flex-wrap items-center justify-center gap-x-4 gap-y-1 bg-action-secondary px-4 py-2 text-center text-sm font-medium text-on-action"
    >
      <span>Demonstração com dados fictícios. Nada é salvo.</span>
      {DEMO_WHATSAPP && (
        <a
          href={`https://wa.me/${DEMO_WHATSAPP}`}
          className="font-semibold underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          Conversar com o assistente de verdade
        </a>
      )}
    </div>
  );
}
