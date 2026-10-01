// Цвета бренда (обложка SB_SplitBill_640x360.png). Дублируют переменные из styles.css —
// здесь они нужны для нативных частей Telegram: шапки, фона и MainButton.
/** Username бота — для ссылок t.me/<bot>?start=… и «добавить в группу». */
export const BOT_USERNAME: string = import.meta.env.VITE_BOT_USERNAME ?? "splitbill66bot";

export const BRAND = {
  bg: "#060608",
  accent: "#e830f8",
  accentInk: "#0b0b0d",
} as const;
