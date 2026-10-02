/**
 * Modo demonstração (ADR-0007): o build com `--mode demo` troca `lib/api.ts` por uma versão 100% em
 * memória (`src/demo/demoApi.ts`), com dados fictícios, sem rede e sem armazenamento no navegador.
 */
export const IS_DEMO = import.meta.env.VITE_DEMO === "true";

/** Só `https:` e `mailto:` viram link; qualquer outro valor (inclusive `javascript:`) é descartado. */
export function safeContactUrl(value: string | undefined): string {
  const url = (value ?? "").trim();
  return /^(https:\/\/|mailto:)\S+$/i.test(url) ? url : "";
}

/** Endereço para pedir uma demonstração à Rovantech (site, formulário ou e-mail); opcional. */
export const DEMO_CONTACT_URL = safeContactUrl(import.meta.env.VITE_DEMO_CONTACT_URL);
