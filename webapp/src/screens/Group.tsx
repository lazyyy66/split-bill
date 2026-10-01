import { useState } from "react";

import { api, type Balances, type Expense, type Group } from "../api";
import { useApp } from "../App";
import { Avatar, ErrorView, Loading, memberName, Money, Row, Section } from "../components";
import { run, useLoad, useMainButton } from "../hooks";
import { parseMoney, toInput } from "../money";
import { haptic } from "../telegram";

type Tab = "balances" | "expenses";

export function GroupScreen({ groupId }: { groupId: string }) {
  const { t } = useApp();
  const { data: group, error, reload } = useLoad(() => api.group(groupId), [groupId]);
  const [tab, setTab] = useState<Tab>("balances");

  if (error) return <ErrorView error={error} onRetry={reload} />;
  if (!group) return <Loading />;
  if (!group.is_member) return <JoinScreen group={group} onJoined={reload} />;

  return (
    <div className="screen">
      <h1 className="title">{group.title}</h1>
      <div className="segmented">
        <button className={tab === "balances" ? "active" : ""} onClick={() => setTab("balances")}>
          {t.balances}
        </button>
        <button className={tab === "expenses" ? "active" : ""} onClick={() => setTab("expenses")}>
          {t.expenses}
        </button>
      </div>
      {tab === "balances" ? <BalancesTab group={group} /> : <ExpensesTab group={group} />}
      <AddExpenseButton group={group} />
    </div>
  );
}

function AddExpenseButton({ group }: { group: Group }) {
  const { t, push } = useApp();
  useMainButton(t.addExpense, () => push({ name: "form", group }));
  return null;
}

function JoinScreen({ group, onJoined }: { group: Group; onJoined: () => void }) {
  const { t } = useApp();
  const [loading, setLoading] = useState(false);
  const join = async () => {
    setLoading(true);
    const ok = await run(() => api.join(group.public_id).then(() => true));
    setLoading(false);
    if (ok) onJoined();
  };
  useMainButton(t.join, join, { loading });
  return (
    <div className="empty">
      <div className="empty-emoji">🙋</div>
      <h2>{group.title}</h2>
      <p className="muted">
        {t.joinTitle}. {t.joinText}
      </p>
    </div>
  );
}

// --- балансы ---

function BalancesTab({ group }: { group: Group }) {
  const { t } = useApp();
  const { data, error, reload } = useLoad(() => api.balances(group.public_id), [group.public_id]);
  if (error) return <ErrorView error={error} onRetry={reload} />;
  if (!data) return <Loading />;

  const name = (id: number) => memberName(group.members, id, group.me_id, t.you);
  const myBalance = data.balances.find((b) => b.user_id === group.me_id)?.amount ?? 0;
  const sorted = [...data.balances].sort((a, b) => b.amount - a.amount);

  return (
    <>
      <div className="hero">
        <div className="hero-label">{myBalance > 0 ? t.youAreOwed : myBalance < 0 ? t.youOwe : t.settled}</div>
        <div className="hero-amount">
          <Money amount={Math.abs(myBalance)} currency={group.currency} />
        </div>
      </div>

      <PendingPayments group={group} balances={data} onChange={reload} />

      <Section title={t.howToSettle}>
        {data.transfers.length === 0 ? (
          <div className="placeholder muted">{t.allSettled}</div>
        ) : (
          data.transfers.map((tr) => (
            <TransferRow key={`${tr.from_user_id}-${tr.to_user_id}`} group={group} transfer={tr} pending={data.pending} onPaid={reload} />
          ))
        )}
      </Section>

      {sorted.length > 0 && (
        <Section title={t.balances}>
          {sorted.map((b) => {
            const member = group.members.find((m) => m.id === b.user_id);
            return (
              <Row
                key={b.user_id}
                left={<Avatar name={member?.name ?? "?"} />}
                title={name(b.user_id)}
                subtitle={member?.left ? t.leftChat : undefined}
                right={<Money amount={b.amount} currency={group.currency} sign colored />}
              />
            );
          })}
        </Section>
      )}
    </>
  );
}

function TransferRow({
  group,
  transfer,
  pending,
  onPaid,
}: {
  group: Group;
  transfer: Balances["transfers"][number];
  pending: Balances["pending"];
  onPaid: () => void;
}) {
  const { t, lang } = useApp();
  const [copied, setCopied] = useState(false);
  const creditor = group.members.find((m) => m.id === transfer.to_user_id);
  const name = (id: number) => memberName(group.members, id, group.me_id, t.you);
  const isMine = transfer.from_user_id === group.me_id;
  const alreadyPending = pending.some(
    (p) => p.from_user_id === transfer.from_user_id && p.to_user_id === transfer.to_user_id,
  );

  const copy = async () => {
    if (!creditor?.payment_details) return;
    await navigator.clipboard.writeText(creditor.payment_details);
    haptic.tap();
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // «Я перевёл» раскрывает поле суммы: по умолчанию вся сумма, можно исправить на частичную
  const [payInput, setPayInput] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const payAmount = payInput === null ? null : parseMoney(payInput, group.currency);
  const pay = async () => {
    if (!payAmount) return;
    setPaying(true);
    const result = await run(() => api.pay(group.public_id, transfer.to_user_id, payAmount));
    setPaying(false);
    if (result) onPaid();
  };

  return (
    <div className="transfer">
      <Row
        title={
          <>
            {name(transfer.from_user_id)} → {name(transfer.to_user_id)}
          </>
        }
        subtitle={creditor?.payment_details ?? t.noDetails}
        right={<Money amount={transfer.amount} currency={group.currency} />}
      />
      <div className="transfer-actions">
        {creditor?.payment_details && (
          <button className="button secondary small" onClick={copy}>
            {copied ? t.copied : t.copyDetails}
          </button>
        )}
        {isMine &&
          (alreadyPending ? (
            <span className="muted small">{t.waitingConfirm}</span>
          ) : payInput === null ? (
            <button className="button small" onClick={() => setPayInput(toInput(transfer.amount, group.currency, lang))}>
              {t.iPaid}
            </button>
          ) : null)}
      </div>
      {payInput !== null && (
        <div className="pay-form">
          <label className="hint">{t.payPartialPrompt}</label>
          <div className="pay-form-row">
            <input
              className="input"
              inputMode="decimal"
              autoFocus
              value={payInput}
              onChange={(e) => setPayInput(e.target.value)}
            />
            <button className="button small" disabled={!payAmount || paying} onClick={pay}>
              {t.iPaid}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function PendingPayments({ group, balances, onChange }: { group: Group; balances: Balances; onChange: () => void }) {
  const { t } = useApp();
  const toMe = balances.pending.filter((p) => p.to_user_id === group.me_id);
  if (toMe.length === 0) return null;

  const resolve = async (id: number, action: "confirm" | "reject") => {
    const result = await run(() => api.resolvePayment(group.public_id, id, action));
    if (result) onChange();
  };

  return (
    <Section title={t.waitingConfirm}>
      {toMe.map((p) => (
        <div className="transfer" key={p.id}>
          <Row
            left={<Avatar name={group.members.find((m) => m.id === p.from_user_id)?.name ?? "?"} />}
            title={memberName(group.members, p.from_user_id, group.me_id, t.you)}
            right={<Money amount={p.amount} currency={group.currency} />}
          />
          <div className="transfer-actions">
            <button className="button secondary small" onClick={() => resolve(p.id, "reject")}>
              {t.notReceived}
            </button>
            <button className="button small" onClick={() => resolve(p.id, "confirm")}>
              {t.received} ✅
            </button>
          </div>
        </div>
      ))}
    </Section>
  );
}

// --- траты ---

function ExpensesTab({ group }: { group: Group }) {
  const { t, lang, push } = useApp();
  const [more, setMore] = useState<Expense[]>([]);
  const [next, setNext] = useState<number | null | undefined>(undefined);
  const { data: firstPage, error, reload } = useLoad(() => api.expenses(group.public_id), [group.public_id]);

  if (error) return <ErrorView error={error} onRetry={reload} />;
  if (!firstPage) return <Loading />;

  const items = [...firstPage.items, ...more];
  const nextCursor = next === undefined ? firstPage.next_before_id : next;
  const loadMore = async () => {
    if (nextCursor === null) return;
    const page = await run(() => api.expenses(group.public_id, nextCursor));
    if (page) {
      setMore((prev) => [...prev, ...page.items]);
      setNext(page.next_before_id);
    }
  };

  if (items.length === 0) return <div className="placeholder muted">{t.noExpenses}</div>;

  const categories = new Map(group.categories.map((c) => [c.id, c]));
  const byDay = new Map<string, Expense[]>();
  for (const e of items) {
    const day = new Date(e.created_at).toLocaleDateString(lang, { day: "numeric", month: "long" });
    byDay.set(day, [...(byDay.get(day) ?? []), e]);
  }

  return (
    <>
      {[...byDay].map(([day, expenses]) => (
        <Section key={day} title={day}>
          {expenses.map((e) => {
            const myShare = e.shares.find((s) => s.user_id === group.me_id)?.amount ?? 0;
            const myImpact = (e.payer_id === group.me_id ? e.amount : 0) - myShare;
            return (
              <Row
                key={e.id}
                left={<div className="emoji">{categories.get(e.category_id)?.emoji ?? "📦"}</div>}
                title={e.title}
                subtitle={`${t.paidByShort} ${memberName(group.members, e.payer_id, group.me_id, t.you)}`}
                right={
                  <div className="stack-right">
                    <Money amount={e.amount} currency={group.currency} />
                    {myImpact !== 0 && (
                      <span className="small">
                        <Money amount={myImpact} currency={group.currency} sign colored />
                      </span>
                    )}
                  </div>
                }
                onClick={() => push({ name: "expense", group, expenseId: e.id })}
              />
            );
          })}
        </Section>
      ))}
      {nextCursor !== null && (
        <button className="button secondary wide" onClick={loadMore}>
          {t.loadMore}
        </button>
      )}
    </>
  );
}
