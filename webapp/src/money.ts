// Деньги — целые числа в минимальных единицах (тиын/копейки), как на бэкенде. Никаких float.

import type { Currency } from "./api";
import type { Lang } from "./i18n";

const NBSP = " ";

/** 1200050 → "12 000,50 ₸" (ru) / "12,000.50 ₸" (en). Повторяет app/domain/money.py. */
export function formatMoney(amount: number, currency: Currency, lang: Lang, opts: { sign?: boolean } = {}): string {
  const unit = 10 ** currency.exponent;
  const abs = Math.abs(amount);
  const major = Math.floor(abs / unit);
  const minor = abs % unit;
  const [thousands, decimal] = lang === "ru" ? [NBSP, ","] : [",", "."];

  let text = String(major).replace(/\B(?=(\d{3})+(?!\d))/g, thousands);
  if (minor) text += decimal + String(minor).padStart(currency.exponent, "0");
  const sign = amount < 0 ? "−" : opts.sign && amount > 0 ? "+" : "";
  return `${sign}${text}${NBSP}${currency.symbol}`;
}

/** "12 000,5" → 1200050. null — если ввод не похож на сумму. */
export function parseMoney(input: string, currency: Currency): number | null {
  const cleaned = input.replace(/[\s ]/g, "").replace(",", ".");
  const match = /^(\d+)(?:\.(\d*))?$/.exec(cleaned);
  if (!match) return null;
  const [, major, minor = ""] = match;
  if (minor.length > currency.exponent) return null;
  const value = Number(major) * 10 ** currency.exponent + Number(minor.padEnd(currency.exponent, "0") || 0);
  return Number.isSafeInteger(value) ? value : null;
}

/** Для поля ввода: 1200050 → "12000,5" (без разделителей тысяч, чтобы легко править). */
export function toInput(amount: number, currency: Currency, lang: Lang): string {
  const unit = 10 ** currency.exponent;
  const major = Math.floor(amount / unit);
  const minor = amount % unit;
  if (!minor) return String(major);
  const decimal = lang === "ru" ? "," : ".";
  return `${major}${decimal}${String(minor).padStart(currency.exponent, "0").replace(/0+$/, "")}`;
}

/** Поровну с остатком плательщику, затем по порядку — как split_equal в app/domain/settlement.py. */
export function splitEqual(total: number, userIds: number[], payerId: number): Map<number, number> {
  const shares = new Map<number, number>();
  if (!userIds.length || total <= 0) return shares;
  const base = Math.floor(total / userIds.length);
  let remainder = total % userIds.length;
  for (const id of userIds) shares.set(id, base);
  const order = userIds.includes(payerId) ? [payerId, ...userIds.filter((id) => id !== payerId)] : userIds;
  for (const id of order) {
    if (remainder-- <= 0) break;
    shares.set(id, (shares.get(id) ?? 0) + 1);
  }
  return shares;
}
