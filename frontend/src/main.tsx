import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import "./index.css";
import { applyTheme, getStoredTheme } from "./lib/theme";

// O <script> do index.html já definiu o tema antes da pintura; aqui só se garante o mesmo valor.
applyTheme(getStoredTheme());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
