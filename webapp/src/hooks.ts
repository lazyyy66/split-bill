import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "./api";
import { alert, haptic, tg } from "./telegram";
import { BRAND } from "./theme";

/** Нативная кнопка Telegram внизу экрана. Вне Telegram (отладка в браузере) — no-op. */
export function useMainButton(text: string | null, onClick: () => void, opts: { loading?: boolean; disabled?: boolean } = {}) {
  const handler = useRef(onClick);
  handler.current = onClick;

  useEffect(() => {
    const button = tg?.MainButton;
    if (!button || text === null) return;
    const cb = () => handler.current();
    button.setParams({ text, color: BRAND.accent, text_color: BRAND.accentInk }).show().onClick(cb);
    return () => {
      button.offClick(cb);
      button.hide();
    };
  }, [text]);

  useEffect(() => {
    const button = tg?.MainButton;
    if (!button || text === null) return;
    if (opts.loading) button.showProgress(false);
    else button.hideProgress();
    if (opts.disabled) button.disable();
    else button.enable();
  }, [text, opts.loading, opts.disabled]);
}

export function useBackButton(onBack: (() => void) | null) {
  const handler = useRef(onBack);
  handler.current = onBack;

  useEffect(() => {
    const button = tg?.BackButton;
    if (!button || !onBack) return;
    const cb = () => handler.current?.();
    button.show();
    button.onClick(cb);
    return () => {
      button.offClick(cb);
      button.hide();
    };
  }, [Boolean(onBack)]);
}

/** Загрузка данных с повтором. reload() — перезапросить. */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    load()
      .then((result) => !cancelled && setData(result))
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, setData, error, reload };
}

/** Выполнить действие с API: ошибку показать человеку, успех — виброоткликом. */
export async function run<T>(action: () => Promise<T>): Promise<T | undefined> {
  try {
    const result = await action();
    haptic.success();
    return result;
  } catch (e) {
    haptic.error();
    await alert(e instanceof Error ? e.message : String(e));
    return undefined;
  }
}
