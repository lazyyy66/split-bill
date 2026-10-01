// Скриншоты всех экранов Mini App без Telegram и без бэкенда:
//   npm run dev -- --port 5174   (в другом окне)
//   node scripts/screenshots.mjs [папка]
// Telegram WebApp подменяется заглушкой (MainButton рисуется внизу, как в Telegram),
// а /api/* отвечает данными из fixtures ниже. Браузер — установленный Microsoft Edge.

import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const BASE = process.env.WEBAPP_URL ?? "http://localhost:5174";
const OUT = process.argv[2] ?? "screenshots";
mkdirSync(OUT, { recursive: true });

// --- данные ---
const KZT = { code: "KZT", symbol: "₸", exponent: 2 };
const ME = 1;
const members = [
  { id: 1, name: "Роман", username: "roman", left: false, payment_details: "Kaspi +7 777 123 45 67" },
  { id: 2, name: "Арман", username: "arman", left: false, payment_details: null },
  { id: 3, name: "Даша", username: "dasha", left: false, payment_details: "+7 701 555 44 33" },
  { id: 4, name: "Тимур", username: null, left: true, payment_details: null },
];
const categories = [
  ["Продукты", "🛒"], ["Кафе и рестораны", "🍽"], ["Транспорт", "🚕"], ["Жильё", "🏠"],
  ["Развлечения", "🎉"], ["Покупки", "🛍"], ["Другое", "📦"],
].map(([name, emoji], i) => ({ id: i + 1, name, emoji, custom: false }));
categories.push({ id: 8, name: "Боулинг", emoji: "🎳", custom: true });

const group = { public_id: "abc", title: "Алматы, март", currency: KZT, is_member: true, me_id: ME, reminder_interval_days: 7, members, categories };
const today = new Date();
const yesterday = new Date(Date.now() - 86_400_000);
const expenses = [
  { id: 6, title: "Ужин в «Дастархане»", amount: 4_850_000, payer_id: 1, category_id: 2, created_by: 1, created_at: today.toISOString(), version: 1,
    shares: [{ user_id: 1, amount: 1_616_668 }, { user_id: 2, amount: 1_616_666 }, { user_id: 3, amount: 1_616_666 }] },
  { id: 5, title: "Такси до Медеу", amount: 320_000, payer_id: 3, category_id: 3, created_by: 3, created_at: today.toISOString(), version: 1,
    shares: [{ user_id: 1, amount: 160_000 }, { user_id: 3, amount: 160_000 }] },
  { id: 4, title: "Квартира на 3 ночи", amount: 13_500_000, payer_id: 1, category_id: 4, created_by: 1, created_at: yesterday.toISOString(), version: 2,
    shares: [{ user_id: 1, amount: 4_500_000 }, { user_id: 2, amount: 4_500_000 }, { user_id: 3, amount: 4_500_000 }] },
  { id: 3, title: "Боулинг", amount: 1_200_000, payer_id: 2, category_id: 8, created_by: 2, created_at: yesterday.toISOString(), version: 1,
    shares: [{ user_id: 1, amount: 300_000 }, { user_id: 2, amount: 300_000 }, { user_id: 3, amount: 300_000 }, { user_id: 4, amount: 300_000 }] },
];
const balances = {
  balances: [{ user_id: 1, amount: 5_766_668 }, { user_id: 2, amount: -4_916_666 }, { user_id: 3, amount: -550_002 }, { user_id: 4, amount: -300_000 }],
  transfers: [
    { from_user_id: 2, to_user_id: 1, amount: 4_916_666 },
    { from_user_id: 3, to_user_id: 1, amount: 550_002 },
    { from_user_id: 4, to_user_id: 1, amount: 300_000 },
  ],
  pending: [{ id: 9, from_user_id: 3, to_user_id: 1, amount: 200_000, status: "pending", created_at: today.toISOString() }],
};
const detail = {
  ...expenses[2],
  history: [
    { action: "create", user_id: 1, created_at: yesterday.toISOString(), snapshot: { amount: 12_000_000 } },
    { action: "update", user_id: 3, created_at: today.toISOString(), snapshot: { amount: 13_500_000 } },
  ],
};
const meUser = { id: ME, name: "Роман", username: "roman", language: "ru", payment_details: "Kaspi +7 777 123 45 67" };
const groupsList = [
  { public_id: "abc", title: "Алматы, март", currency: KZT, my_balance: 5_766_668 },
  { public_id: "def", title: "Квартира на Абая", currency: KZT, my_balance: -1_250_000 },
  { public_id: "ghi", title: "ДР Даши", currency: KZT, my_balance: 0 },
];

// --- заглушка Telegram WebApp ---
function telegramStub({ startParam }) {
  const listeners = { main: new Set(), back: new Set() };
  const makeButton = (kind) => {
    const state = { text: "", visible: false, progress: false, color: null, textColor: null };
    const render = () => {
      if (kind !== "main") return;
      let el = document.getElementById("__tg_main");
      if (!el) {
        el = document.createElement("div");
        el.id = "__tg_main";
        el.style.cssText =
          "position:fixed;left:0;right:0;bottom:0;padding:8px 16px 20px;background:var(--tg-bottom-bar,#000);z-index:9999;font:600 16px -apple-system,Segoe UI,sans-serif";
        el.innerHTML = '<div style="border-radius:12px;padding:14px;text-align:center"></div>';
        el.onclick = () => listeners.main.forEach((cb) => cb());
        document.body.appendChild(el);
      }
      el.style.display = state.visible ? "block" : "none";
      const inner = el.firstChild;
      inner.textContent = state.progress ? "…" : state.text;
      inner.style.background = state.color ?? "#2481cc";
      inner.style.color = state.textColor ?? "#fff";
    };
    const api = {
      setText: (t) => ((state.text = t), render(), api),
      setParams: (p) => (Object.assign(state, { text: p.text ?? state.text, color: p.color ?? state.color, textColor: p.text_color ?? state.textColor }), render(), api),
      show: () => ((state.visible = true), render(), api),
      hide: () => ((state.visible = false), render(), api),
      enable: () => api, disable: () => api,
      showProgress: () => ((state.progress = true), render(), api),
      hideProgress: () => ((state.progress = false), render(), api),
      onClick: (cb) => (listeners[kind].add(cb), api),
      offClick: (cb) => (listeners[kind].delete(cb), api),
    };
    return api;
  };
  window.Telegram = {
    WebApp: {
      initData: "query_id=stub&user=%7B%7D&auth_date=1&hash=stub",
      initDataUnsafe: { user: { id: 1, first_name: "Роман", language_code: "ru" }, start_param: startParam },
      colorScheme: "dark",
      themeParams: {},
      version: "8.0",
      MainButton: makeButton("main"),
      BackButton: { show() {}, hide() {}, onClick(cb) { listeners.back.add(cb); }, offClick(cb) { listeners.back.delete(cb); } },
      HapticFeedback: { impactOccurred() {}, notificationOccurred() {}, selectionChanged() {} },
      ready() {}, expand() {}, close() {}, disableVerticalSwipes() {},
      setHeaderColor() {}, setBackgroundColor() {},
      setBottomBarColor(c) { document.documentElement.style.setProperty("--tg-bottom-bar", c); },
      showAlert(m, cb) { console.log("ALERT", m); cb?.(); },
      showConfirm(m, cb) { cb(true); },
      openTelegramLink() {},
      isVersionAtLeast: () => true,
      __back: () => listeners.back.forEach((cb) => cb()),
    },
  };
}

async function api(route) {
  const url = new URL(route.request().url());
  const path = url.pathname.replace(/^\/api/, "");
  const json = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  const scenario = route.request().headers()["x-scenario"];
  if (path === "/me") return json({ user: meUser, groups: globalThis.__emptyHome ? [] : groupsList });
  if (path === "/groups/join-me") return json({ ...group, public_id: "join-me", title: "Поездка на Иссык-Куль", is_member: false, members: [], categories: [] });
  if (path === "/groups/abc") return json(group);
  if (path === "/groups/abc/balances") return json(balances);
  if (path === "/groups/abc/expenses") return json({ items: expenses, next_before_id: null });
  if (path.startsWith("/groups/abc/expenses/")) return json(detail);
  void scenario;
  return json({ code: "err_not_found", message: "Не найдено" }, 404);
}

const browser = await chromium.launch({ channel: "msedge" });

// FULL_PAGE=0 — только экран телефона (для лендинга), иначе — вся страница целиком (для проверки вёрстки)
const FULL_PAGE_DEFAULT = process.env.FULL_PAGE !== "0";

async function shot(name, { startParam, emptyHome = false, steps = async () => {}, fullPage = FULL_PAGE_DEFAULT } = {}) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    locale: "ru-RU",
  });
  const page = await context.newPage();
  page.on("console", (m) => m.type() === "error" && console.log(`  [${name}] console:`, m.text()));
  page.on("pageerror", (e) => console.log(`  [${name}] pageerror:`, e.message));
  await page.route("https://telegram.org/**", (r) => r.fulfill({ contentType: "application/javascript", body: "" }));
  globalThis.__emptyHome = emptyHome;
  await page.route("**/api/**", api);
  await page.addInitScript(telegramStub, { startParam });
  await page.goto(BASE);
  await page.waitForLoadState("networkidle");
  await steps(page);
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage });
  await context.close();
  console.log("✓", name);
}

await shot("01-home", {});
await shot("02-home-empty", { emptyHome: true });
await shot("03-group-balances", { startParam: "g_abc" });
await shot("04-group-expenses", {
  startParam: "g_abc",
  steps: async (p) => p.getByRole("button", { name: "Траты" }).click(),
});
await shot("05-expense-detail", {
  startParam: "g_abc",
  steps: async (p) => {
    await p.getByRole("button", { name: "Траты" }).click();
    await p.getByText("Квартира на 3 ночи").click();
  },
});
await shot("06-form-equal", {
  startParam: "g_abc",
  steps: async (p) => {
    await p.locator("#__tg_main").click();
    await p.locator(".amount-input input").fill("15000");
    await p.getByPlaceholder(/Ужин/).fill("Продукты на неделю");
  },
});
await shot("07-form-exact", {
  startParam: "g_abc",
  steps: async (p) => {
    await p.locator("#__tg_main").click();
    await p.locator(".amount-input input").fill("15000");
    await p.getByRole("button", { name: "Точные суммы" }).click();
  },
});
await shot("08-join", { startParam: "g_join-me" });
await shot("09-pay-form", {
  startParam: "g_abc",
  steps: async (p) => {
    // смотрим глазами Армана нельзя (me_id фиксирован) — показываем раскрытую форму через кнопку у себя нет;
    // поэтому раскрываем только копирование реквизитов
    await p.getByRole("button", { name: /Скопировать/ }).first().click().catch(() => {});
  },
  fullPage: false,
});

await browser.close();
