import { useState } from "react";

import { translateText } from "../lib/api";
import { TranslateIcon } from "./icons";

/**
 * Botão "Traduzir" sob um balão recebido em outro idioma: busca a tradução sob demanda (nada é
 * gravado) e mostra embaixo do balão. Clicar de novo esconde, sem pedir à API outra vez.
 */
export function TranslateToggle({ texto }: Readonly<{ texto: string }>) {
  const [state, setState] = useState<
    { kind: "idle" } | { kind: "loading" } | { kind: "shown"; traducao: string } | { kind: "error" }
  >({ kind: "idle" });

  async function toggle() {
    if (state.kind === "shown") {
      setState({ kind: "idle" });
      return;
    }
    setState({ kind: "loading" });
    const result = await translateText(texto, "pt");
    setState(result.ok ? { kind: "shown", traducao: result.data } : { kind: "error" });
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={toggle}
        disabled={state.kind === "loading"}
        aria-pressed={state.kind === "shown"}
        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-md px-1 text-xs font-semibold text-link hover:underline disabled:text-muted"
      >
        <TranslateIcon />
        {state.kind === "shown" ? "Ocultar tradução" : "Traduzir"}
      </button>
      {state.kind === "loading" && <p className="text-xs text-muted">Traduzindo…</p>}
      {state.kind === "error" && (
        <p role="alert" className="text-xs text-status-error">
          Não foi possível traduzir agora.
        </p>
      )}
      {state.kind === "shown" && (
        <p className="flex flex-col gap-0.5 rounded-md border border-subtle bg-subtle px-3 py-2 text-sm text-primary">
          <span className="text-xs font-semibold uppercase tracking-wide text-secondary">
            Tradução automática
          </span>
          {state.traducao}
        </p>
      )}
    </div>
  );
}
