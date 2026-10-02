import { DEMO_CONTACT_URL } from "../lib/demo";

/**
 * Faixa fixa da demonstração: deixa claro que os dados são fictícios e que o assistente não
 * responde de verdade aqui, e leva a quem quer ver o produto real (a Rovantech mostra numa demo).
 */
export function DemoBanner() {
  return (
    <div
      role="note"
      className="sticky top-0 z-sticky flex flex-wrap items-center justify-center gap-x-4 gap-y-1 bg-action-secondary px-4 py-2 text-center text-sm font-medium text-on-action"
    >
      <p>
        <strong className="font-semibold">Demonstração com dados fictícios. Nada é salvo.</strong>{" "}
        As respostas do assistente são exemplos fixos, não uma IA ao vivo. Para ver os dados reais e
        o assistente respondendo de verdade, entre em contato com a Rovantech e solicite uma
        demonstração.
      </p>
      {DEMO_CONTACT_URL && (
        <a
          href={DEMO_CONTACT_URL}
          className="font-semibold underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          Falar com a Rovantech
        </a>
      )}
    </div>
  );
}
