import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { initAuth } from "./auth";
import { ToastProvider } from "./components/ui";
import "./styles.css";

const root = ReactDOM.createRoot(document.getElementById("root")!);

// Finish (or start) Cognito sign-in before the first API call. A no-op in local dev mode.
initAuth()
  .then(() =>
    root.render(
      <React.StrictMode>
        <BrowserRouter>
          <ToastProvider>
            <App />
          </ToastProvider>
        </BrowserRouter>
      </React.StrictMode>,
    ),
  )
  .catch((e: Error) => root.render(<p style={{ padding: 24 }}>{e.message}</p>));
