import { defineConfig } from "@playwright/test";

const PANEL_URL = "http://localhost:4173";
const DEMO_URL = "http://localhost:4174";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  // O painel real e a demonstração pública (ADR-0007) são dois builds, cada um com seu servidor.
  projects: [
    { name: "panel", testIgnore: /demo\.spec\.ts/, use: { baseURL: PANEL_URL } },
    { name: "demo", testMatch: /demo\.spec\.ts/, use: { baseURL: DEMO_URL } },
  ],
  webServer: [
    {
      command: "npm run build && npm run preview",
      url: PANEL_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run build:demo && npm run preview:demo",
      url: DEMO_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
