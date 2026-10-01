import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";
import { tg } from "./telegram";

tg?.ready();
tg?.expand();
tg?.disableVerticalSwipes?.(); // свайп вниз не закрывает приложение, пока заполняешь форму

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
