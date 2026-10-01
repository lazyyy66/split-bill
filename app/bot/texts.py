"""Тексты бота на русском и английском. Ключ → {язык: шаблон}. Подстановки — через str.format."""

TEXTS: dict[str, dict[str, str]] = {
    # --- приветствие и участники ---
    "welcome": {
        "ru": (
            "👋 Привет! Я считаю общие траты компании и говорю, кто кому сколько должен.\n\n"
            "1. Каждый жмёт <b>«Я в деле 🙋»</b>\n"
            "2. Траты: <code>/add 12000 продукты</code> — поровну на всех\n"
            "3. <code>/balance</code> — кто сколько должен\n"
            "4. <code>/settle</code> — как рассчитаться минимумом переводов\n\n"
            "Свой номер для переводов: <code>/setpay +7 777 123 45 67</code>\n\n"
            "<b>В деле:</b> {members}"
        ),
        "en": (
            "👋 Hi! I track shared expenses and tell who owes whom.\n\n"
            "1. Everyone taps <b>“I'm in 🙋”</b>\n"
            "2. Expenses: <code>/add 12000 groceries</code> — split equally\n"
            "3. <code>/balance</code> — who owes what\n"
            "4. <code>/settle</code> — settle up with the fewest transfers\n\n"
            "Your payment details: <code>/setpay +7 777 123 45 67</code>\n\n"
            "<b>In:</b> {members}"
        ),
    },
    "nobody_yet": {"ru": "пока никого", "en": "nobody yet"},
    "btn_join": {"ru": "Я в деле 🙋", "en": "I'm in 🙋"},
    "joined": {"ru": "Ты в деле!", "en": "You're in!"},
    "already_joined": {"ru": "Ты уже в деле 👌", "en": "You're already in 👌"},
    "private_start": {
        "ru": (
            "👋 Я работаю в групповых чатах: добавь меня в чат компании, и я буду считать общие траты.\n\n"
            "Здесь можно указать номер для переводов: <code>/setpay +7 777 123 45 67</code>"
        ),
        "en": (
            "👋 I work in group chats: add me to your friends' chat and I'll track shared expenses.\n\n"
            "Here you can set your payment details: <code>/setpay +7 777 123 45 67</code>"
        ),
    },
    "group_only": {"ru": "Эта команда работает в групповом чате.", "en": "This command works in group chats."},
    "not_set_up": {
        "ru": "Я ещё не знаю эту группу — отправьте /start.",
        "en": "I don't know this group yet — send /start.",
    },
    # --- /add ---
    "add_usage": {
        "ru": "Формат: <code>/add 12000 продукты</code>\nСумма без пробелов, копейки через точку или запятую.",
        "en": "Usage: <code>/add 12000 groceries</code>\nAmount without spaces, cents after a dot or comma.",
    },
    "add_alone": {
        "ru": "Пока в деле только ты. Пусть остальные нажмут «Я в деле 🙋» (/start), тогда будет на кого делить.",
        "en": "You're the only one in so far. Ask others to tap “I'm in 🙋” (/start) so there's someone to split with.",
    },
    "expense_added": {
        "ru": "{emoji} <b>{title}</b> — {amount}\nПлатил(а): {payer}\nДелим на {count}: {per_person}",
        "en": "{emoji} <b>{title}</b> — {amount}\nPaid by: {payer}\nSplit between {count}: {per_person}",
    },
    "per_person_equal": {"ru": "по {amount}", "en": "{amount} each"},
    "per_person_about": {"ru": "примерно по {amount}", "en": "about {amount} each"},
    "default_title": {"ru": "Трата", "en": "Expense"},
    "btn_cancel_expense": {"ru": "Отменить", "en": "Undo"},
    "expense_deleted": {
        "ru": "🗑 <s>{title} — {amount}</s>\nОтменил(а): {by}",
        "en": "🗑 <s>{title} — {amount}</s>\nUndone by: {by}",
    },
    "expense_not_found": {"ru": "Трата уже удалена", "en": "Expense already deleted"},
    "members_only": {
        "ru": "Сначала нажми «Я в деле 🙋»",
        "en": "Tap “I'm in 🙋” first",
    },
    # --- /balance ---
    "balance_header": {"ru": "📊 <b>Балансы</b>", "en": "📊 <b>Balances</b>"},
    "balance_empty": {"ru": "Трат пока нет — все в расчёте ✨", "en": "No expenses yet — everyone is settled ✨"},
    "balance_settled": {"ru": "Все в расчёте ✨", "en": "Everyone is settled ✨"},
    "left_mark": {"ru": " (вышел из чата)", "en": " (left the chat)"},
    "balance_hint": {"ru": "Как рассчитаться — /settle", "en": "How to settle up — /settle"},
    # --- /settle ---
    "settle_header": {
        "ru": "💸 <b>Как рассчитаться</b> ({count} перев.):",
        "en": "💸 <b>How to settle up</b> ({count} transfers):",
    },
    "settle_line": {"ru": "{debtor} → {creditor}: <b>{amount}</b>", "en": "{debtor} → {creditor}: <b>{amount}</b>"},
    "settle_pay_details": {"ru": "   реквизиты: <code>{details}</code>", "en": "   details: <code>{details}</code>"},
    "settle_footer": {
        "ru": "Перевёл? Нажми кнопку — получатель подтвердит.\nЧастично: <code>/paid 3000 @username</code>",
        "en": "Paid? Tap the button — the recipient will confirm.\nPartial: <code>/paid 3000 @username</code>",
    },
    "btn_paid": {"ru": "✅ {debtor} → {creditor} {amount}", "en": "✅ {debtor} → {creditor} {amount}"},
    "btn_copy": {"ru": "📋 Номер {name}", "en": "📋 {name}'s details"},
    "settle_outdated": {
        "ru": "Долги уже изменились — вызови /settle заново",
        "en": "Balances have changed — run /settle again",
    },
    "settlement_already_pending": {
        "ru": "Этот перевод уже ждёт подтверждения",
        "en": "This transfer is already waiting for confirmation",
    },
    "not_your_debt": {"ru": "Эту кнопку жмёт тот, кто переводит", "en": "Only the sender can tap this"},
    # --- переводы ---
    "paid_usage": {
        "ru": "Формат: <code>/paid 3000 @username</code> или ответом на сообщение получателя: <code>/paid 3000</code>",
        "en": "Usage: <code>/paid 3000 @username</code> or reply to the recipient's message: <code>/paid 3000</code>",
    },
    "paid_unknown_user": {
        "ru": "Не нашёл {username} среди участников. Пусть нажмёт «Я в деле 🙋».",
        "en": "Can't find {username} among members. Ask them to tap “I'm in 🙋”.",
    },
    "settlement_pending": {
        "ru": "💸 {debtor} перевёл(а) {creditor} <b>{amount}</b>\n{creditor}, подтверди 👇",
        "en": "💸 {debtor} sent {creditor} <b>{amount}</b>\n{creditor}, please confirm 👇",
    },
    "btn_confirm": {"ru": "Получил ✅", "en": "Received ✅"},
    "btn_reject": {"ru": "Не получал ❌", "en": "Not received ❌"},
    "settlement_confirmed": {
        "ru": "✅ {debtor} → {creditor}: <b>{amount}</b> — получено",
        "en": "✅ {debtor} → {creditor}: <b>{amount}</b> — received",
    },
    "settlement_rejected": {
        "ru": "❌ {debtor} → {creditor}: <s>{amount}</s> — {creditor} не получил(а) перевод",
        "en": "❌ {debtor} → {creditor}: <s>{amount}</s> — {creditor} didn't receive it",
    },
    # --- /setpay, /lang ---
    "setpay_usage": {
        "ru": (
            "Укажи номер, на который тебе переводить (Kaspi, телефон или карта):\n"
            "<code>/setpay +7 777 123 45 67</code>\n\nСейчас: {current}"
        ),
        "en": (
            "Set where people should send you money (phone, card, etc.):\n"
            "<code>/setpay +7 777 123 45 67</code>\n\nCurrent: {current}"
        ),
    },
    "setpay_none": {"ru": "не указано", "en": "not set"},
    "setpay_saved": {"ru": "Сохранил: <code>{details}</code>", "en": "Saved: <code>{details}</code>"},
    "setpay_too_long": {"ru": "Слишком длинно, максимум 64 символа", "en": "Too long, 64 characters max"},
    "lang_usage": {
        "ru": "Язык: <code>/lang ru</code> или <code>/lang en</code>",
        "en": "Language: <code>/lang ru</code> or <code>/lang en</code>",
    },
    "lang_set": {"ru": "Готово, говорю по-русски 🇷🇺", "en": "Done, speaking English 🇬🇧"},
    # --- ошибки сервисов ---
    "err_self_transfer": {"ru": "Нельзя перевести самому себе", "en": "You can't pay yourself"},
    "err_settlement_not_found": {"ru": "Перевод не найден", "en": "Transfer not found"},
    "err_not_recipient": {"ru": "Подтвердить может только получатель", "en": "Only the recipient can confirm"},
    "err_already_resolved": {"ru": "Перевод уже обработан", "en": "Already handled"},
    "err_amount": {"ru": "Сумма должна быть больше нуля", "en": "Amount must be positive"},
    "err_conflict": {
        "ru": "Кто-то изменил это одновременно с тобой — попробуй ещё раз",
        "en": "Someone changed this at the same time — try again",
    },
    # --- категории ---
    "cat_groceries": {"ru": "Продукты", "en": "Groceries"},
    "cat_cafe": {"ru": "Кафе и рестораны", "en": "Restaurants"},
    "cat_transport": {"ru": "Транспорт", "en": "Transport"},
    "cat_housing": {"ru": "Жильё", "en": "Housing"},
    "cat_fun": {"ru": "Развлечения", "en": "Entertainment"},
    "cat_shopping": {"ru": "Покупки", "en": "Shopping"},
    "cat_other": {"ru": "Другое", "en": "Other"},
}

LANGUAGES = ("ru", "en")


def t(lang: str, key: str, **kwargs: object) -> str:
    variants = TEXTS[key]
    template = variants.get(lang) or variants["ru"]
    return template.format(**kwargs) if kwargs else template
