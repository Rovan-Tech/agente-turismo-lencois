// @vitest-environment node
import { build, type Rollup } from "vite";
import { beforeAll, describe, expect, it } from "vitest";

/**
 * O pacote da demonstração (ADR-0007) nasce de um build real em modo `demo`: nele não pode haver
 * endereço de backend, token nem chamada à API, e o navegador precisa recusar qualquer rede.
 */
let files: { name: string; text: string }[] = [];

beforeAll(async () => {
  const result = (await build({
    mode: "demo",
    logLevel: "silent",
    build: { write: false, outDir: "dist-demo-test" },
  })) as Rollup.RollupOutput | Rollup.RollupOutput[];
  const outputs = Array.isArray(result) ? result.flatMap((r) => r.output) : result.output;
  files = outputs.map((file) => ({
    name: file.fileName,
    text: file.type === "chunk" ? file.code : String(file.source),
  }));
}, 60_000);

const bundle = () => files.filter((f) => f.name.startsWith("assets/") || f.name === "index.html");

describe("demonstration bundle", () => {
  it("carries no backend address, token or API path", () => {
    const joined = bundle()
      .map((f) => f.text)
      .join("\n");

    expect(joined).not.toMatch(/run\.app/);
    expect(joined).not.toMatch(/\/api\//);
    expect(joined).not.toMatch(/Authorization|Bearer|VITE_API_TOKEN|VITE_API_BASE_URL/);
  });

  it("says on every screen shell that the data is fictional", () => {
    const script = bundle().find((f) => f.name.endsWith(".js"));

    expect(script?.text).toContain("Demonstração com dados fictícios. Nada é salvo.");
  });

  it("tells the browser to refuse fetch and forms, and to run only the known inline script", async () => {
    const headers = files.find((f) => f.name === "_headers")?.text ?? "";
    const html = files.find((f) => f.name === "index.html")?.text ?? "";
    const inline = /<script>([\s\S]*?)<\/script>/.exec(html)?.[1] ?? "";
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(inline));
    const hash = `'sha256-${btoa(String.fromCharCode(...new Uint8Array(digest)))}'`;

    expect(headers).toContain("connect-src 'none'");
    expect(headers).toContain("default-src 'self'");
    expect(headers).toContain("form-action 'none'");
    expect(headers).toContain("frame-ancestors 'none'");
    expect(headers).toContain(`script-src 'self' ${hash}`);
    expect(inline).not.toBe("");
  });
});
