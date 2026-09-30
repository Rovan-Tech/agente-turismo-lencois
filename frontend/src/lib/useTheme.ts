import { useCallback, useEffect, useState } from "react";

import { applyTheme, getStoredTheme, saveTheme, type Theme } from "./theme";

/**
 * Tema atual e a função que alterna claro/escuro. A escolha só é gravada quando a pessoa clica:
 * gravar na montagem transformaria o padrão em "escolha" e o prenderia se o padrão mudasse.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    saveTheme(next);
    setTheme(next);
  }, [theme]);

  return [theme, toggle] as const;
}
