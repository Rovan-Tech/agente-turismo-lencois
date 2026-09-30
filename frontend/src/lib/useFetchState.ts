import { useCallback, useEffect, useRef, useState } from "react";

export type FetchState<T> =
  { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

/**
 * Busca dados assíncronos distinguindo carregando/erro/sucesso, com proteção contra `setState`
 * após desmontar (tanto na busca inicial quanto no `refetch` devolvido).
 *
 * `fetchFn` só é lido na montagem (como as demais páginas já fazem) — trocar a função a cada
 * render não dispara um novo fetch.
 */
export function useFetchState<T>(fetchFn: () => Promise<T | null>) {
  const [state, setState] = useState<FetchState<T>>({ status: "loading" });
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const applyResult = useCallback((data: T | null) => {
    if (!mountedRef.current) return;
    setState(data === null ? { status: "error" } : { status: "ready", data });
  }, []);

  const refetch = useCallback(async () => {
    applyResult(await fetchFn());
  }, [applyResult]);

  useEffect(() => {
    fetchFn().then(applyResult);
  }, [applyResult]);

  return [state, refetch] as const;
}
