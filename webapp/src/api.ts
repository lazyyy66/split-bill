// Клиент API. Авторизация — подписанный initData из Telegram в заголовке Authorization: tma <initData>.

import { tg } from "./telegram";

export interface Currency {
  code: string;
  symbol: string;
  exponent: number;
}

export interface MeUser {
  id: number;
  name: string;
  username: string | null;
  language: "ru" | "en";
  payment_details: string | null;
}

export interface GroupSummary {
  public_id: string;
  title: string;
  currency: Currency;
  my_balance: number;
}

export interface Member {
  id: number;
  name: string;
  username: string | null;
  left: boolean;
  payment_details: string | null;
}

export interface Category {
  id: number;
  name: string;
  emoji: string;
  custom: boolean;
}

export interface Group {
  public_id: string;
  title: string;
  currency: Currency;
  is_member: boolean;
  me_id: number;
  members: Member[];
  categories: Category[];
}

export interface Settlement {
  id: number;
  from_user_id: number;
  to_user_id: number;
  amount: number;
  status: "pending" | "confirmed" | "rejected";
  created_at: string;
}

export interface Balances {
  balances: { user_id: number; amount: number }[];
  transfers: { from_user_id: number; to_user_id: number; amount: number }[];
  pending: Settlement[];
}

export interface Share {
  user_id: number;
  amount: number;
}

export interface Expense {
  id: number;
  title: string;
  amount: number;
  payer_id: number;
  category_id: number;
  created_by: number;
  created_at: string;
  version: number;
  shares: Share[];
}

export interface ExpenseDetail extends Expense {
  history: { action: "create" | "update" | "delete"; user_id: number; created_at: string; snapshot: Record<string, unknown> }[];
}

export type Split = { mode: "equal"; user_ids: number[] } | { mode: "exact"; shares: Share[] };

export interface ExpenseInput {
  title: string;
  amount: number;
  category_id: number;
  payer_id: number;
  split: Split;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      Authorization: `tma ${tg?.initData ?? ""}`,
      ...(body !== undefined && { "Content-Type": "application/json" }),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    // 422 — ошибка схемы (FastAPI), у неё нет нашего code/message
    throw new ApiError(response.status, data.code ?? "err_unknown", data.message ?? `HTTP ${response.status}`);
  }
  return data as T;
}

const g = (id: string) => `/groups/${encodeURIComponent(id)}`;

export const api = {
  me: () => request<{ user: MeUser; groups: GroupSummary[] }>("GET", "/me"),
  updateMe: (patch: Partial<Pick<MeUser, "language" | "payment_details">>) => request<MeUser>("PATCH", "/me", patch),

  group: (id: string) => request<Group>("GET", g(id)),
  join: (id: string) => request<void>("POST", `${g(id)}/join`),
  balances: (id: string) => request<Balances>("GET", `${g(id)}/balances`),
  addCategory: (id: string, name: string, emoji: string) =>
    request<Category>("POST", `${g(id)}/categories`, { name, emoji }),

  expenses: (id: string, beforeId?: number) =>
    request<{ items: Expense[]; next_before_id: number | null }>(
      "GET",
      `${g(id)}/expenses${beforeId ? `?before_id=${beforeId}` : ""}`,
    ),
  expense: (id: string, expenseId: number) => request<ExpenseDetail>("GET", `${g(id)}/expenses/${expenseId}`),
  createExpense: (id: string, input: ExpenseInput) => request<Expense>("POST", `${g(id)}/expenses`, input),
  updateExpense: (id: string, expenseId: number, input: ExpenseInput & { version: number }) =>
    request<Expense>("PUT", `${g(id)}/expenses/${expenseId}`, input),
  deleteExpense: (id: string, expenseId: number, version: number) =>
    request<void>("DELETE", `${g(id)}/expenses/${expenseId}?version=${version}`),

  pay: (id: string, toUserId: number, amount: number) =>
    request<Settlement>("POST", `${g(id)}/settlements`, { to_user_id: toUserId, amount }),
  resolvePayment: (id: string, settlementId: number, action: "confirm" | "reject") =>
    request<Settlement>("POST", `${g(id)}/settlements/${settlementId}/${action}`),
};
