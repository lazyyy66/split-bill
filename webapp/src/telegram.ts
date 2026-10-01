// Тонкая типизированная обёртка над window.Telegram.WebApp (скрипт telegram-web-app.js в index.html).
// https://core.telegram.org/bots/webapps

interface BottomButton {
  setText(text: string): BottomButton;
  setParams(params: { text?: string; color?: string; text_color?: string; has_shine_effect?: boolean }): BottomButton;
  show(): BottomButton;
  hide(): BottomButton;
  enable(): BottomButton;
  disable(): BottomButton;
  showProgress(leaveActive?: boolean): BottomButton;
  hideProgress(): BottomButton;
  onClick(cb: () => void): BottomButton;
  offClick(cb: () => void): BottomButton;
}

interface BackButton {
  show(): void;
  hide(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}

interface WebApp {
  initData: string;
  initDataUnsafe: {
    user?: { id: number; first_name: string; language_code?: string };
    start_param?: string;
  };
  colorScheme: "light" | "dark";
  MainButton: BottomButton;
  BackButton: BackButton;
  HapticFeedback: {
    impactOccurred(style: "light" | "medium" | "heavy" | "rigid" | "soft"): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
    selectionChanged(): void;
  };
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  setBottomBarColor?(color: string): void;
  ready(): void;
  expand(): void;
  close(): void;
  showAlert(message: string, cb?: () => void): void;
  showConfirm(message: string, cb: (ok: boolean) => void): void;
  openTelegramLink(url: string): void;
  disableVerticalSwipes?(): void;
  isVersionAtLeast(version: string): boolean;
}

declare global {
  interface Window {
    Telegram?: { WebApp: WebApp };
  }
}

export const tg: WebApp | undefined = window.Telegram?.WebApp;

/** Открыто внутри Telegram (есть подписанные данные)? */
export const insideTelegram = Boolean(tg?.initData);

export function alert(message: string): Promise<void> {
  return new Promise((resolve) => (tg ? tg.showAlert(message, () => resolve()) : (window.alert(message), resolve())));
}

export function confirm(message: string): Promise<boolean> {
  return new Promise((resolve) => (tg ? tg.showConfirm(message, resolve) : resolve(window.confirm(message))));
}

export const haptic = {
  success: () => tg?.HapticFeedback.notificationOccurred("success"),
  error: () => tg?.HapticFeedback.notificationOccurred("error"),
  tap: () => tg?.HapticFeedback.selectionChanged(),
};
