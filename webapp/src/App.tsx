import { createContext, useContext, useMemo, useState } from "react";

import type { Expense, Group, MeUser } from "./api";
import { useBackButton } from "./hooks";
import { detectLang, type Lang, texts, type Texts } from "./i18n";
import { ExpenseDetailScreen } from "./screens/ExpenseDetail";
import { ExpenseFormScreen } from "./screens/ExpenseForm";
import { GroupScreen } from "./screens/Group";
import { HomeScreen } from "./screens/Home";
import { insideTelegram, tg } from "./telegram";

export type Route =
  | { name: "home" }
  | { name: "group"; groupId: string }
  | { name: "expense"; group: Group; expenseId: number }
  | { name: "form"; group: Group; expense?: Expense };

interface AppContext {
  lang: Lang;
  t: Texts;
  me: MeUser | null;
  setMe: (me: MeUser) => void;
  push: (route: Route) => void;
  pop: () => void;
}

const Ctx = createContext<AppContext | null>(null);

export function useApp(): AppContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp вне <App>");
  return ctx;
}

/** Ссылка из группы: t.me/<bot>/<app>?startapp=g_<public_id> → сразу открываем эту группу. */
function initialStack(): Route[] {
  const param = tg?.initDataUnsafe.start_param;
  if (param?.startsWith("g_")) return [{ name: "home" }, { name: "group", groupId: param.slice(2) }];
  return [{ name: "home" }];
}

export function App() {
  const [stack, setStack] = useState<Route[]>(initialStack);
  const [me, setMe] = useState<MeUser | null>(null);
  const lang: Lang = me?.language ?? detectLang(tg?.initDataUnsafe.user?.language_code);

  const ctx = useMemo<AppContext>(
    () => ({
      lang,
      t: texts[lang],
      me,
      setMe,
      push: (route) => setStack((s) => [...s, route]),
      pop: () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
    }),
    [lang, me],
  );

  useBackButton(stack.length > 1 ? ctx.pop : null);

  if (!insideTelegram) {
    return <div className="center muted">{texts[lang].openInTelegram}</div>;
  }

  const route = stack[stack.length - 1];
  return (
    <Ctx.Provider value={ctx}>
      {/* key — чтобы экран перемонтировался (и перезагрузил данные) при возврате назад */}
      <Screen key={stack.length} route={route} />
    </Ctx.Provider>
  );
}

function Screen({ route }: { route: Route }) {
  switch (route.name) {
    case "home":
      return <HomeScreen />;
    case "group":
      return <GroupScreen groupId={route.groupId} />;
    case "expense":
      return <ExpenseDetailScreen group={route.group} expenseId={route.expenseId} />;
    case "form":
      return <ExpenseFormScreen group={route.group} expense={route.expense} />;
  }
}
