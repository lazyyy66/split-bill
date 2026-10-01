import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";
import { tg } from "./telegram";
import { BRAND } from "./theme";

// Шапка, фон и нижняя панель Telegram — в цветах бренда (тёмная тема всегда)
tg?.setHeaderColor?.(BRAND.bg);
tg?.setBackgroundColor?.(BRAND.bg);
tg?.setBottomBarColor?.(BRAND.bg);
tg?.ready();
tg?.expand();
tg?.disableVerticalSwipes?.(); // свайп вниз не закрывает приложение, пока заполняешь форму

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
