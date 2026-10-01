import { api, type Group } from "../api";
import { useApp } from "../App";
import { ErrorView, Loading, memberName, Money, Row, Section } from "../components";
import { useLoad, useMainButton } from "../hooks";

/** Трата в виде чека: сумма, кто платил, доли «с точками», ниже — история изменений. */
export function ExpenseDetailScreen({ group, expenseId }: { group: Group; expenseId: number }) {
  const { t, lang, push } = useApp();
  const { data: expense, error, reload } = useLoad(() => api.expense(group.public_id, expenseId), [expenseId]);
  useMainButton(expense ? t.edit : null, () => expense && push({ name: "form", group, expense }));

  if (error) return <ErrorView error={error} onRetry={reload} />;
  if (!expense) return <Loading />;

  const name = (id: number) => memberName(group.members, id, group.me_id, t.you);
  const category = group.categories.find((c) => c.id === expense.category_id);
  const date = (iso: string) =>
    new Date(iso).toLocaleString(lang, { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
  const historyLabel = { create: t.historyCreate, update: t.historyUpdate, delete: t.historyDelete };

  return (
    <div className="screen">
      <div className="receipt" style={{ marginTop: 12 }}>
        <div className="receipt-emoji">{category?.emoji ?? "📦"}</div>
        <div className="eyebrow">{category?.name}</div>
        <h1 className="page-title" style={{ margin: "6px 0 0" }}>
          {expense.title}
        </h1>
        <div className="receipt-amount">
          <Money amount={expense.amount} currency={group.currency} />
        </div>
        <div className="receipt-meta">
          {t.paidByShort} {name(expense.payer_id)} · {date(expense.created_at)}
        </div>

        <div className="receipt-lines">
          {[...expense.shares]
            .sort((a, b) => b.amount - a.amount)
            .map((share) => (
              <div className="receipt-line" key={share.user_id}>
                <span>{name(share.user_id)}</span>
                <span className="leader" />
                <Money amount={share.amount} currency={group.currency} />
              </div>
            ))}
        </div>
      </div>

      <Section title={t.history}>
        {expense.history.map((h, i) => (
          <Row
            key={i}
            title={
              <>
                {name(h.user_id)} <span className="muted">{historyLabel[h.action]}</span>
              </>
            }
            subtitle={date(h.created_at)}
            right={
              typeof h.snapshot.amount === "number" ? (
                <span className="muted">
                  <Money amount={h.snapshot.amount} currency={group.currency} />
                </span>
              ) : undefined
            }
          />
        ))}
      </Section>
    </div>
  );
}
