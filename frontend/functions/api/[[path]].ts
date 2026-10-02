import { handleApiProxy, type ProxyEnv } from "../../src/lib/apiProxy";

/** Pages Function de `/api/*`: repassa o painel ao Cloud Run (ver `src/lib/apiProxy.ts`). */
export function onRequest(context: { request: Request; env: ProxyEnv }): Promise<Response> {
  return handleApiProxy(context.request, context.env);
}
