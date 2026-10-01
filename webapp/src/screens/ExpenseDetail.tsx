import { api, type Group } from "../api";
import { useApp } from "../App";
import { Avatar, ErrorView, Loading, memberName, Money, Row, Section } from "../components";
import { useLoad, useMainButton } from "../hooks";

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
      <div className="hero">
        <div className="hero-emoji">{category?.emoji ?? "📦"}</div>
        <div className="hero-label">{expense.title}</div>
        <div className="hero-amount">
          <Money amount={expense.amount} currency={group.currency} />
        </div>
        <div className="muted small">
          {t.paidByShort} {name(expense.payer_id)} · {date(expense.created_at)}
        </div>
      </div>

      <Section title={t.shares}>
        {[...expense.shares]
          .sort((a, b) => b.amount - a.amount)
          .map((share) => (
            <Row
              key={share.user_id}
              left={<Avatar name={group.members.find((m) => m.id === share.user_id)?.name ?? "?"} />}
              title={name(share.user_id)}
              right={<Money amount={share.amount} currency={group.currency} />}
            />
          ))}
      </Section>

      <Section title={t.history}>
        {expense.history.map((h, i) => (
          <Row
            key={i}
            title={
              <>
                {name(h.user_id)} {historyLabel[h.action]}
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
