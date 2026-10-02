import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import { demoPlugins } from "./demo/vitePlugin.ts";

// `--mode demo` gera a demonstração pública (ADR-0007): dados em memória, sem rede nem backend.
export default defineConfig(({ mode }) => {
  const isDemo = mode === "demo";
  return {
    plugins: [react(), ...(isDemo ? demoPlugins() : [])],
    define: isDemo ? { "import.meta.env.VITE_DEMO": JSON.stringify("true") } : {},
    build: isDemo ? { outDir: "dist-demo" } : {},
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
      exclude: ["tests/e2e/**", "node_modules/**"],
      coverage: {
        provider: "v8",
        include: ["src/**"],
        exclude: ["src/main.tsx", "src/vite-env.d.ts", "src/types.ts"],
        reporter: ["text-summary", "json-summary", "cobertura", "lcov"],
        reportsDirectory: "coverage",
      },
    },
  };
});
