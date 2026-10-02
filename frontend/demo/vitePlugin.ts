import type { Plugin } from "vite";

const REAL_API = decodeURIComponent(new URL("../src/lib/api.ts", import.meta.url).pathname);
const DEMO_API = decodeURIComponent(new URL("../src/demo/demoApi.ts", import.meta.url).pathname);
const INLINE_SCRIPT = /<script>([\s\S]*?)<\/script>/g;

/** Hash do CSP para um script inline: `'sha256-<base64 do SHA-256 do texto>'`. */
async function cspHash(script: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(script));
  return `'sha256-${btoa(String.fromCharCode(...new Uint8Array(digest)))}'`;
}

/**
 * Troca `src/lib/api.ts` pela versão em memória em qualquer importação (ADR-0007): o arquivo real,
 * com os endereços da API, nem entra no pacote da demonstração.
 */
function swapApi(): Plugin {
  return {
    name: "demo-swap-api",
    enforce: "pre",
    async resolveId(source, importer, options) {
      const resolved = await this.resolve(source, importer, { ...options, skipSelf: true });
      return resolved?.id === REAL_API ? DEMO_API : null;
    },
  };
}

/**
 * Cabeçalhos do Pages para a demonstração: `connect-src 'none'` faz o navegador recusar fetch, XHR e
 * WebSocket (as fontes do Google, por CSS, são a única rede externa), mesmo que um dia o código tente. O script do tema (inline, antes da pintura) é
 * liberado pelo hash, não por `unsafe-inline`.
 */
function demoHeaders(): Plugin {
  return {
    name: "demo-headers",
    enforce: "post",
    async generateBundle(_options, bundle) {
      const html = Object.values(bundle).find((file) => file.fileName === "index.html");
      const source = html && "source" in html ? String(html.source) : "";
      const hashes = await Promise.all(
        [...source.matchAll(INLINE_SCRIPT)].map((m) => cspHash(m[1]))
      );
      const policy = [
        "default-src 'self'",
        `script-src 'self' ${hashes.join(" ")}`.trim(),
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
      ].join("; ");
      this.emitFile({
        type: "asset",
        fileName: "_headers",
        source: `/*\n  Content-Security-Policy: ${policy}\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n`,
      });
    },
  };
}

export function demoPlugins(): Plugin[] {
  return [swapApi(), demoHeaders()];
}
