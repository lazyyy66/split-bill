// Картинки для README из HTML-исходников в docs/images/src (+ скриншот опубликованного лендинга).
//   node scripts/readme-images.mjs [имя ...]   — без аргументов собирает всё
// Браузер — установленный Microsoft Edge (Playwright без скачивания своего Chromium).

import { readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = join(root, "docs/images/src");
const out = join(root, "docs/images");
const only = new Set(process.argv.slice(2));

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 1600, height: 1000 } });

for (const file of readdirSync(src).filter((f) => f.endsWith(".html"))) {
  const name = file.replace(/\.html$/, "");
  if (only.size && !only.has(name)) continue;
  await page.goto(pathToFileURL(join(src, file)).href);
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.locator("#canvas").screenshot({ path: join(out, `${name}.png`) });
  console.log("✓", name);
}

if (!only.size || only.has("landing")) {
  const landing = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 1280, height: 760 } });
  await landing.goto("https://lazyyy66.github.io/split-bill/");
  await landing.evaluate(() => document.fonts.ready);
  await landing.waitForTimeout(2800); // чек «допечатывается»
  await landing.screenshot({ path: join(out, "landing.png") });
  console.log("✓ landing");
}

await browser.close();
