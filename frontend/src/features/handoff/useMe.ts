import { useEffect, useState } from "react";

import { getMe } from "../../lib/api";
import type { Me } from "../../types";

/** Quem está logado; `null` enquanto carrega ou se a consulta falhar (o painel segue sem o nome). */
export function useMe(): Me | null {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    let active = true;
    getMe().then((data) => {
      if (active) setMe(data);
    });
    return () => {
      active = false;
    };
  }, []);
  return me;
}
