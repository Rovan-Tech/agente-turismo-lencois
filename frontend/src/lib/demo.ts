/**
 * Modo demonstração (ADR-0007): o build com `--mode demo` troca `lib/api.ts` por uma versão 100% em
 * memória (`src/demo/demoApi.ts`), com dados fictícios, sem rede e sem armazenamento no navegador.
 */
export const IS_DEMO = import.meta.env.VITE_DEMO === "true";

/** Só dígitos (DDI + DDD + número) do WhatsApp da agência; sem ele o botão de contato some. */
export const DEMO_WHATSAPP = (import.meta.env.VITE_DEMO_WHATSAPP ?? "").replace(/\D/g, "");
