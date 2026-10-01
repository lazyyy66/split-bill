// Переключение RU / EN. Русский текст лежит прямо в HTML (видно без JS и поисковикам),
// английский — здесь. Выбор запоминается; по умолчанию — язык браузера.
(() => {
  const en = {
    skip: "Skip to content",
    heroTitle: "Split the bill — keep the friends",
    heroLead:
      "A Telegram bot for shared expenses. Add it to your group chat, log expenses in a couple of taps, and at the end it tells everyone who pays whom and how much.",
    ctaAdd: "Add to a chat",
    ctaOpen: "Open the bot",
    heroNote: "Free. Nothing to install.",
    receiptTrip: "Almaty, March",
    receiptPeople: "Roman, Arman, Dasha",
    r1: "Apartment, 3 nights",
    r2: "Dinner at Dastarkhan",
    r3: "Bowling",
    r4: "Taxi to Medeu",
    receiptTotal: "Total, 66 300 ₸ each",
    receiptSettle: "Two transfers settle everything",
    t1: "Dasha → Roman",
    t2: "Arman → Roman",
    howTitle: "How it works",
    s1Title: "Add the bot to your chat",
    s1Text: "Everyone taps “I’m in”, so the bot knows who to split with.",
    s2Title: "Log expenses",
    s2Text:
      "Type <code>/add 12000 dinner</code> right in the chat or use the form in the app: split equally, between some people, or by exact amounts.",
    s3Title: "Settle up",
    s3Text:
      "The bot reduces debts to the fewest transfers. The recipient’s details copy in one tap, and a debt closes when they tap “Received”.",
    featuresTitle: "What it does",
    f1Title: "Everything inside Telegram",
    f1Text: "No app to install, no sign-up. The chat you already use is enough.",
    f2Title: "Fewest transfers",
    f2Text: "Instead of a dozen “I owe you, you owe him” — two or three transfers for the whole group.",
    f3Title: "Details in one tap",
    f3Text: "Everyone sets where to receive money: phone or card. In the debt list, it copies right away.",
    f4Title: "Confirmed payments",
    f4Text: "A transfer counts only after the recipient taps “Received”. Partial payments are fine.",
    f5Title: "Reminders",
    f5Text: "Once a week the bot privately reminds people what they owe. Change how often, or turn it off.",
    f6Title: "Excel spreadsheet",
    f6Text: "All expenses, everyone’s shares and transfers in one file, sent to your private chat.",
    f7Title: "Edit history",
    f7Text: "Anyone in the group can fix an expense, and you can see who changed it and when.",
    f8Title: "Russian and English",
    f8Text: "The language follows your Telegram settings; switch it with <code>/lang</code>.",
    faqTitle: "Questions",
    q1: "Is it free?",
    a1: "Yes, completely.",
    q2: "Does the bot read our chat?",
    a2: "No. In groups, Telegram only passes the bot commands addressed to it, like <code>/add</code> or <code>/balance</code>. Regular messages stay invisible to it.",
    q3: "Can we split unevenly?",
    a3: "Yes. In the app, pick who took part, or enter an exact amount for each person.",
    q4: "What if someone leaves the chat?",
    a4: "They stay in the balances until their debt is settled, but aren’t included in new expenses.",
    q5: "Which currency?",
    a5: "Tenge for now. Cents (tiyn) are counted exactly, with no rounding along the way.",
    q6: "How do I delete my data?",
    a6: 'Message us on <a href="https://github.com/lazyyy66/split-bill/issues">GitHub</a> and we’ll delete it. What we store is described in the <a href="privacy.html">privacy policy</a>.',
    finalTitle: "Your next trip — without “who owes whom”",
    privacy: "Privacy",
  };
  const titles = { ru: document.title, en: document.title.includes("Конфиденциальность") ? "Privacy — SplitBill" : "SplitBill — shared expenses in Telegram" };

  const ru = {};
  const nodes = document.querySelectorAll("[data-i18n], [data-i18n-html]");
  // Запоминаем русский оригинал, чтобы переключаться обратно без перезагрузки
  nodes.forEach((node) => {
    const key = node.dataset.i18n ?? node.dataset.i18nHtml;
    ru[key] = node.innerHTML;
  });

  function apply(lang) {
    const dict = lang === "en" ? en : ru;
    nodes.forEach((node) => {
      const key = node.dataset.i18n ?? node.dataset.i18nHtml;
      if (dict[key] !== undefined) node.innerHTML = dict[key];
    });
    document.documentElement.lang = lang;
    document.title = titles[lang];
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
    });
    try {
      localStorage.setItem("lang", lang);
    } catch {
      /* приватный режим — просто не запоминаем */
    }
  }

  let saved = null;
  try {
    saved = localStorage.getItem("lang");
  } catch {
    /* ignore */
  }
  const browserRu = /^(ru|uk|be|kk|uz|ky)\b/i.test(navigator.language || "");
  apply(saved ?? (browserRu ? "ru" : "en"));

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => apply(button.dataset.lang));
  });
})();
