import type { ReactNode } from "react";

import type { Currency, Member } from "./api";
import { useApp } from "./App";
import { formatMoney } from "./money";

export function Section({
  title,
  children,
  extra,
  bare,
}: {
  title?: string;
  children: ReactNode;
  extra?: ReactNode;
  bare?: boolean;
}) {
  return (
    <section className="section">
      {(title || extra) && (
        <div className="section-header">
          <span className="eyebrow">{title}</span>
          {extra}
        </div>
      )}
      <div className={`section-body${bare ? " bare" : ""}`}>{children}</div>
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
      {left}
      <div className="row-main">
        <div className="row-title">{title}</div>
        {subtitle && <div className="row-subtitle">{subtitle}</div>}
      </div>
      {right !== undefined && <div className="row-right">{right}</div>}
    </div>
  );
}

/** colored: «тебе должны» — пурпурным, «ты должен» — обычным цветом со знаком минус, ноль — приглушённо. */
export function Money({
  amount,
  currency,
  sign,
  colored,
}: {
  amount: number;
  currency: Currency;
  sign?: boolean;
  colored?: boolean;
}) {
  const { lang } = useApp();
  const cls = colored ? (amount > 0 ? "positive" : amount === 0 ? "zero" : "") : "";
  return <span className={`money ${cls}`}>{formatMoney(amount, currency, lang, { sign })}</span>;
}

/** Тёмный «шар» с инициалом — как кружки с людьми на обложке. Свой — с пурпурным кольцом. */
export function Avatar({ name, me, small }: { name: string; me?: boolean; small?: boolean }) {
  return (
    <div className={`avatar${me ? " me" : ""}${small ? " small" : ""}`}>
      {name.trim().charAt(0).toUpperCase() || "?"}
    </div>
  );
}

export function AvatarPair({ from, to, meId }: { from: Member | undefined; to: Member | undefined; meId: number }) {
  return (
    <div className="pair">
      <Avatar name={from?.name ?? "?"} me={from?.id === meId} small />
      <span className="pair-arrow">→</span>
      <Avatar name={to?.name ?? "?"} me={to?.id === meId} small />
    </div>
  );
}

export function Brand() {
  const { lang } = useApp();
  return (
    <div className="brand">
      <div className="brand-mark">
        S<span className="slash">/</span>B
      </div>
      <div>
        <div className="brand-name">SplitBill</div>
        <div className="brand-tagline">
          {lang === "ru" ? "Раздели платёж — сохрани дружбу" : "Split the bill — keep the friends"}
        </div>
      </div>
    </div>
  );
}

/** Три человека и пурпурные стрелки по кругу — мотив обложки. */
export function CycleIllustration() {
  const person = (cx: number, cy: number) => (
    <g key={`${cx}-${cy}`}>
      <circle cx={cx} cy={cy} r="24" fill="url(#ball)" stroke="rgb(255 255 255 / 8%)" />
      <circle cx={cx} cy={cy - 6} r="7" fill="#9c9ca2" />
      <path d={`M${cx - 12} ${cy + 13} a12 10 0 0 1 24 0 z`} fill="#9c9ca2" />
    </g>
  );
  return (
    <svg className="cycle" viewBox="0 0 168 150" aria-hidden="true">
      <defs>
        <radialGradient id="ball" cx="35%" cy="30%" r="75%">
          <stop offset="0" stopColor="#2c2c33" />
          <stop offset="0.7" stopColor="#141418" />
        </radialGradient>
        <marker id="tip" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" fill="#e830f8" />
        </marker>
      </defs>
      <g fill="none" stroke="#e830f8" strokeWidth="4" strokeLinecap="round" markerEnd="url(#tip)">
        <path d="M102 26 Q132 30 140 58" />
        <path d="M128 118 Q108 136 80 130" />
        <path d="M30 104 Q20 76 40 52" />
      </g>
      {person(70, 34)}
      {person(136, 92)}
      {person(42, 120)}
    </svg>
  );
}

export function memberName(members: Member[], id: number, meId: number, youLabel: string): string {
  const member = members.find((m) => m.id === id);
  const name = member?.name ?? "?";
  return id === meId ? `${name} (${youLabel})` : name;
}

export function Loading() {
  return (
    <div className="screen" aria-busy="true">
      <div className="skeleton" style={{ height: 28, width: "45%", margin: "8px 0 24px" }} />
      <div className="skeleton" style={{ height: 150, marginBottom: 22 }} />
      <div className="skeleton" style={{ height: 64, marginBottom: 10 }} />
      <div className="skeleton" style={{ height: 64 }} />
    </div>
  );
}

export function ErrorView({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const { t } = useApp();
  return (
    <div className="center">
      <p className="muted">{error.message}</p>
      <button className="button ghost" onClick={onRetry}>
        {t.retry}
      </button>
    </div>
  );
}
