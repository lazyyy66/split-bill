import { useEffect, useState } from "react";

import { api } from "../api";
import { useApp } from "../App";
import { Avatar, Brand, CycleIllustration, ErrorView, Loading, Money, Row, Section } from "../components";
import { run, useLoad } from "../hooks";
import type { Lang } from "../i18n";
import { haptic, tg } from "../telegram";
import { BOT_USERNAME } from "../theme";

export function HomeScreen() {
  const { t, setMe, push } = useApp();
  const { data, error, reload } = useLoad(() => api.me(), []);

  useEffect(() => {
    if (data) setMe(data.user);
  }, [data, setMe]);

  if (error) return <ErrorView error={error} onRetry={reload} />;
  if (!data) return <Loading />;

  // Итог по всем группам — только если валюта везде одна (иначе складывать нельзя)
  const currencies = new Set(data.groups.map((g) => g.currency.code));
  const total = currencies.size === 1 ? data.groups.reduce((sum, g) => sum + g.my_balance, 0) : null;

  return (
    <div className="screen">
      <Brand />

      {data.groups.length === 0 ? (
        <div className="empty">
          <CycleIllustration />
          <h2>{t.noGroupsTitle}</h2>
          <p>{t.noGroupsText}</p>
          <button
            className="button"
            onClick={() => tg?.openTelegramLink(`https://t.me/${BOT_USERNAME}?startgroup=true`)}
          >
            {t.addToGroup}
          </button>
        </div>
      ) : (
        <>
          {total !== null && (
            <div className="receipt">
              <div className="eyebrow">{total > 0 ? t.youAreOwed : total < 0 ? t.youOwe : t.settled}</div>
              <div className={`receipt-amount${total > 0 ? " positive" : ""}`}>
                <Money amount={Math.abs(total)} currency={data.groups[0].currency} />
              </div>
              <div className="receipt-meta">
                {t.inGroups} {data.groups.length}
              </div>
            </div>
          )}
          <Section title={t.myGroups}>
            {data.groups.map((group) => (
              <Row
                key={group.public_id}
                left={<Avatar name={group.title} />}
                title={group.title}
                subtitle={group.my_balance > 0 ? t.youAreOwed : group.my_balance < 0 ? t.youOwe : t.settled}
                right={<Money amount={group.my_balance} currency={group.currency} sign colored />}
                onClick={() => push({ name: "group", groupId: group.public_id })}
              />
            ))}
          </Section>
        </>
      )}

      <PaymentDetails initial={data.user.payment_details} />
      <LanguageSwitch />
    </div>
  );
}

function PaymentDetails({ initial }: { initial: string | null }) {
  const { t, setMe } = useApp();
  const [value, setValue] = useState(initial ?? "");
  const [saving, setSaving] = useState(false);
  const changed = value.trim() !== (initial ?? "");

  const save = async () => {
    setSaving(true);
    const me = await run(() => api.updateMe({ payment_details: value.trim() || null }));
    setSaving(false);
    if (me) setMe(me);
  };

  return (
    <Section title={t.paymentDetails}>
      <div className="field">
        <input
          className="input"
          value={value}
          maxLength={64}
          placeholder="Kaspi +7 777 123 45 67"
          onChange={(e) => setValue(e.target.value)}
        />
        <div className="hint">{t.paymentDetailsHint}</div>
        {changed && (
          <button className="button small" disabled={saving} onClick={save}>
            {t.save}
          </button>
        )}
      </div>
    </Section>
  );
}

function LanguageSwitch() {
  const { t, lang, setMe } = useApp();
  const select = async (next: Lang) => {
    if (next === lang) return;
    haptic.tap();
    const me = await run(() => api.updateMe({ language: next }));
    if (me) setMe(me);
  };
  return (
    <Section title={t.language} bare>
      <div className="segmented">
        {(["ru", "en"] as const).map((code) => (
          <button key={code} className={code === lang ? "active" : ""} onClick={() => select(code)}>
            {code === "ru" ? "Русский" : "English"}
          </button>
        ))}
      </div>
    </Section>
  );
}
