import { useMemo, useState } from "react";

import { api, type Category, type Expense, type ExpenseInput, type Group } from "../api";
import { useApp } from "../App";
import { Avatar, Money, Section } from "../components";
import { run, useMainButton } from "../hooks";
import { parseMoney, splitEqual, toInput } from "../money";
import { alert, confirm, haptic } from "../telegram";

type Mode = "equal" | "exact";

export function ExpenseFormScreen({ group, expense }: { group: Group; expense?: Expense }) {
  const { t, lang, pop } = useApp();
  const currency = group.currency;
  const [categories, setCategories] = useState<Category[]>(group.categories);

  // Участники: активные + те, кто уже есть в этой трате (даже если вышли из чата)
  const people = useMemo(
    () => group.members.filter((m) => !m.left || expense?.shares.some((s) => s.user_id === m.id) || expense?.payer_id === m.id),
    [group.members, expense],
  );

  const [amountInput, setAmountInput] = useState(expense ? toInput(expense.amount, currency, lang) : "");
  const [title, setTitle] = useState(expense?.title ?? "");
  const [categoryId, setCategoryId] = useState(
    expense?.category_id ?? categories.filter((c) => !c.custom).at(-1)?.id ?? categories[0]?.id,
  );
  const [payerId, setPayerId] = useState(expense?.payer_id ?? group.me_id);
  const initialEqual = !expense || isEqualSplit(expense);
  const [mode, setMode] = useState<Mode>(initialEqual ? "equal" : "exact");
  const [selected, setSelected] = useState<Set<number>>(
    new Set(expense ? expense.shares.map((s) => s.user_id) : people.filter((m) => !m.left).map((m) => m.id)),
  );
  const [exact, setExact] = useState<Record<number, string>>(() =>
    Object.fromEntries((expense?.shares ?? []).map((s) => [s.user_id, toInput(s.amount, currency, lang)])),
  );
  const [saving, setSaving] = useState(false);

  const amount = parseMoney(amountInput, currency) ?? 0;
  const selectedIds = people.filter((m) => selected.has(m.id)).map((m) => m.id);
  const equalShares = splitEqual(amount, selectedIds, payerId);
  const exactAmounts = Object.fromEntries(people.map((m) => [m.id, parseMoney(exact[m.id] ?? "", currency) ?? 0]));
  const exactSum = Object.values(exactAmounts).reduce((a, b) => a + b, 0);
  const remaining = amount - exactSum;

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    haptic.tap();
    if (next === "exact") {
      // переносим текущий равный делёж в поля — дальше человек правит
      setExact(Object.fromEntries(people.map((m) => [m.id, equalShares.has(m.id) ? toInput(equalShares.get(m.id)!, currency, lang) : ""])));
    }
    setMode(next);
  };

  const toggle = (id: number) => {
    haptic.tap();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const save = async () => {
    if (amount <= 0) return alert(t.invalidAmount);
    if (!title.trim()) return alert(t.invalidTitle);
    if (mode === "equal" && selectedIds.length === 0) return alert(t.splitBetween);
    if (mode === "exact" && remaining !== 0) return alert(`${t.remaining}: ${remaining / 10 ** currency.exponent}`);

    const input: ExpenseInput = {
      title: title.trim(),
      amount,
      category_id: categoryId!,
      payer_id: payerId,
      split:
        mode === "equal"
          ? { mode: "equal", user_ids: selectedIds }
          : { mode: "exact", shares: people.map((m) => ({ user_id: m.id, amount: exactAmounts[m.id] })) },
    };
    setSaving(true);
    const result = await run(() =>
      expense
        ? api.updateExpense(group.public_id, expense.id, { ...input, version: expense.version })
        : api.createExpense(group.public_id, input),
    );
    setSaving(false);
    if (result) pop();
  };

  const remove = async () => {
    if (!expense || !(await confirm(t.deleteConfirm))) return;
    const ok = await run(() => api.deleteExpense(group.public_id, expense.id, expense.version).then(() => true));
    if (ok) pop();
  };

  useMainButton(t.save, save, { loading: saving });

  return (
    <div className="screen">
      <h1 className="page-title">{expense ? t.editExpense : t.newExpense}</h1>

      <div className="amount-input">
        {/* Невидимая копия текста задаёт ширину поля — так ₸ стоит вплотную к сумме */}
        <label className="amount-sizer" data-value={amountInput || "0"}>
        <input
          inputMode="decimal"
          placeholder="0"
          autoFocus={!expense}
          size={1}
          value={amountInput}
          onChange={(e) => setAmountInput(e.target.value)}
        />
        </label>
        <span className="currency">{currency.symbol}</span>
      </div>

      <Section>
        <input
          className="input plain"
          placeholder={t.titlePlaceholder}
          maxLength={128}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </Section>

      <Section title={t.category} bare>
        <CategoryPicker group={group} categories={categories} value={categoryId} onChange={setCategoryId} onCreated={(c) => setCategories((prev) => [...prev, c])} />
      </Section>

      <Section title={t.paidBy} bare>
        <div className="chips">
          {people.map((m) => (
            <button key={m.id} className={`chip${m.id === payerId ? " active" : ""}`} onClick={() => setPayerId(m.id)}>
              {m.id === group.me_id ? `${m.name} (${t.you})` : m.name}
            </button>
          ))}
        </div>
      </Section>

      <Section
        title={t.splitBetween}
        extra={
          <div className="segmented compact">
            <button className={mode === "equal" ? "active" : ""} onClick={() => switchMode("equal")}>
              {t.splitEqual}
            </button>
            <button className={mode === "exact" ? "active" : ""} onClick={() => switchMode("exact")}>
              {t.splitExact}
            </button>
          </div>
        }
      >
        {people.map((m) => (
          <div key={m.id} className="row">
            <Avatar name={m.name} me={m.id === group.me_id} />
            <div className="row-main">
              <div className="row-title">{m.id === group.me_id ? `${m.name} (${t.you})` : m.name}</div>
            </div>
            <div className="row-right">
              {mode === "equal" ? (
                <label className="check">
                  {selected.has(m.id) && amount > 0 && (
                    <span className="muted small">
                      <Money amount={equalShares.get(m.id) ?? 0} currency={currency} />
                    </span>
                  )}
                  <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} />
                </label>
              ) : (
                <input
                  className="input share-input"
                  inputMode="decimal"
                  placeholder="0"
                  value={exact[m.id] ?? ""}
                  onChange={(e) => setExact((prev) => ({ ...prev, [m.id]: e.target.value }))}
                />
              )}
            </div>
          </div>
        ))}
        {mode === "exact" && remaining !== 0 && (
          <div className={`remaining${remaining < 0 ? " over" : ""}`}>
            <span>{remaining > 0 ? t.remaining : t.overBy}</span>
            <Money amount={Math.abs(remaining)} currency={currency} />
          </div>
        )}
      </Section>

      {expense && (
        <button className="button danger wide" onClick={remove}>
          {t.delete}
        </button>
      )}
    </div>
  );
}

function isEqualSplit(expense: Expense): boolean {
  const amounts = expense.shares.map((s) => s.amount);
  return Math.max(...amounts) - Math.min(...amounts) <= 1;
}

function CategoryPicker({
  group,
  categories,
  value,
  onChange,
  onCreated,
}: {
  group: Group;
  categories: Category[];
  value: number | undefined;
  onChange: (id: number) => void;
  onCreated: (category: Category) => void;
}) {
  const { t } = useApp();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [emoji, setEmoji] = useState("");

  const create = async () => {
    const category = await run(() => api.addCategory(group.public_id, name.trim(), emoji.trim() || "🏷"));
    if (!category) return;
    onCreated(category);
    onChange(category.id);
    setAdding(false);
    setName("");
    setEmoji("");
  };

  return (
    <>
      <div className="chips">
        {categories.map((c) => (
          <button
            key={c.id}
            className={`chip${c.id === value ? " active" : ""}`}
            onClick={() => {
              haptic.tap();
              onChange(c.id);
            }}
          >
            {c.emoji} {c.name}
          </button>
        ))}
        <button className={`chip dashed${adding ? " active" : ""}`} onClick={() => setAdding((v) => !v)}>
          ＋ {t.newCategory}
        </button>
      </div>
      {adding && (
        <div className="pay-form-row" style={{ marginTop: 12 }}>
          <input className="input emoji-input" placeholder="🎳" maxLength={8} value={emoji} onChange={(e) => setEmoji(e.target.value)} />
          <input
            className="input"
            placeholder={t.newCategoryName}
            maxLength={32}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="button small" disabled={!name.trim()} onClick={create}>
            {t.save}
          </button>
        </div>
      )}
    </>
  );
}
