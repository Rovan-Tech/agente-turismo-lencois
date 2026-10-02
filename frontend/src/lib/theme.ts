import { IS_DEMO } from "./demo";

export type Theme = "light" | "dark";

const STORAGE_KEY = "painel-tema";

/**
 * Tema salvo pela pessoa; sem escolha, claro (como no desenho), ignorando a preferência do
 * sistema. O armazenamento pode estar bloqueado (aba privada), então falhar não pode quebrar.
 */
export function getStoredTheme(): Theme {
  // A demonstração não grava nada no navegador (ADR-0007): o tema vale só nesta aba.
  if (IS_DEMO) return "light";
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function saveTheme(theme: Theme): void {
  if (IS_DEMO) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Sem armazenamento: o tema vale só nesta sessão.
  }
}

/** Os tokens de `tokens.css` trocam de cor conforme o atributo `data-theme` da página. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}
