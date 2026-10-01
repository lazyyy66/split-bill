import type { ReactNode } from "react";

import type { Currency, Member } from "./api";
import { useApp } from "./App";
import { formatMoney } from "./money";

export function Section({ title, children, extra }: { title?: string; children: ReactNode; extra?: ReactNode }) {
  return (
    <section className="section">
      {(title || extra) && (
        <div className="section-header">
          <span>{title}</span>
          {extra}
        </div>
      )}
      <div className="section-body">{children}</div>
    </section>
  );
}

export function Row({
  left,
  title,
  subtitle,
  right,
  onClick,
}: {
  left?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div className={`row${onClick ? " clickable" : ""}`} onClick={onClick}>
      {left !== undefined && <div className="row-left">{left}</div>}
      <div className="row-main">
        <div className="row-title">{title}</div>
        {subtitle && <div className="row-subtitle">{subtitle}</div>}
      </div>
      {right !== undefined && <div className="row-right">{right}</div>}
    </div>
  );
}

export function Money({ amount, currency, sign, colored }: { amount: number; currency: Currency; sign?: boolean; colored?: boolean }) {
  const { lang } = useApp();
  const cls = colored ? (amount > 0 ? "positive" : amount < 0 ? "negative" : "muted") : "";
  return <span className={`money ${cls}`}>{formatMoney(amount, currency, lang, { sign })}</span>;
}

export function Avatar({ name }: { name: string }) {
  // Цвет — стабильный по имени, чтобы человек везде был одного цвета
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  const hue = Math.abs(hash) % 360;
  return (
    <div className="avatar" style={{ background: `hsl(${hue} 55% 55%)` }}>
      {name.trim().charAt(0).toUpperCase() || "?"}
    </div>
  );
}

export function memberName(members: Member[], id: number, meId: number, youLabel: string): string {
  const member = members.find((m) => m.id === id);
  const name = member?.name ?? "?";
  return id === meId ? `${name} (${youLabel})` : name;
}

export function Loading() {
  const { t } = useApp();
  return <div className="center muted">{t.loading}</div>;
}

export function ErrorView({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const { t } = useApp();
  return (
    <div className="center">
      <p className="muted">{error.message}</p>
      <button className="button secondary" onClick={onRetry}>
        {t.retry}
      </button>
    </div>
  );
}
