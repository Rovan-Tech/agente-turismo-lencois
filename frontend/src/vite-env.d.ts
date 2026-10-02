/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_TOKEN?: string;
  readonly VITE_DEMO?: string;
  readonly VITE_DEMO_WHATSAPP?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
