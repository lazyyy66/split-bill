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
            "💳 Номер, на который тебе переводить, — кнопка ниже\n\n"
            "<b>В деле:</b> {members}"
        ),
        "en": (
            "👋 Hi! I track shared expenses and tell who owes whom.\n\n"
            "1. Everyone taps <b>“I'm in 🙋”</b>\n"
            "2. Expenses: <code>/add 12000 groceries</code> — split equally\n"
            "3. <code>/balance</code> — who owes what\n"
            "4. <code>/settle</code> — settle up with the fewest transfers\n\n"
            "💳 Where people should send you money — button below\n\n"
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
            "Номер для переводов: /setpay"
        ),
        "en": (
            "👋 I work in group chats: add me to your friends' chat and I'll track shared expenses.\n\n"
            "Payment details: /setpay"
        ),
    },
    "group_only": {"ru": "Эта команда работает в групповом чате.", "en": "This command works in group chats."},
    "not_set_up": {
        "ru": "Я ещё не знаю эту группу — отправьте /start.",
        "en": "I don't know this group yet — send /start.",
    },
    # --- /add ---
    "add_usage": {
        "ru": (
            "Формат: <code>/add 12000 продукты</code>\n"
            "Сумму можно с пробелами (12 000), копейки — через точку или запятую."
        ),
        "en": (
            "Usage: <code>/add 12000 groceries</code>\n"
            "Spaces in the amount are fine (12 000), cents after a dot or comma."
        ),
    },
    "add_alone": {
        "ru": "Пока в деле только ты. Пусть остальные нажмут «Я в деле 🙋» (/start), тогда будет на кого делить.",
        "en": "You're the only one in so far. Ask others to tap “I'm in 🙋” (/start) so there's someone to split with.",
    },
    "expense_added": {
        "ru": "{emoji} <b>{title}</b> — {amount}\nПлатил(а): {payer}\nДелим на {count}: {per_person}",
        "en": "{emoji} <b>{title}</b> — {amount}\nPaid by: {payer}\nSplit between {count}: {per_person}",
    },
    "expense_added_by": {"ru": "Добавил(а): {by}", "en": "Added by: {by}"},
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
    "btn_copy": {"ru": "📋 Реквизиты: {name}", "en": "📋 Details: {name}"},
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
    # --- напоминания ---
    "reminder_dm": {
        "ru": (
            "⏰ Напоминание из «{group}»\n\n"
            "Ты должен(а):\n{lines}\n\n"
            "Перевёл? Отметь в приложении — получатель подтвердит."
        ),
        "en": (
            "⏰ Reminder from “{group}”\n\n"
            "You owe:\n{lines}\n\n"
            "Paid already? Mark it in the app — the recipient will confirm."
        ),
    },
    "reminder_line": {"ru": "• {name} — <b>{amount}</b>", "en": "• {name} — <b>{amount}</b>"},
    "reminder_group": {
        "ru": ("⏰ <b>Напоминание о долгах</b>\n{lines}\n\nЧтобы получать напоминания в личку, напишите мне /start."),
        "en": ("⏰ <b>Debt reminder</b>\n{lines}\n\nTo get reminders privately, send me /start."),
    },
    "reminder_group_line": {
        "ru": "{debtor} → {creditor}: <b>{amount}</b>",
        "en": "{debtor} → {creditor}: <b>{amount}</b>",
    },
    # --- экспорт ---
    "export_sent_group": {
        "ru": "📄 Отправил таблицу в личку, {name}.",
        "en": "📄 Sent the spreadsheet to your private chat, {name}.",
    },
    "export_need_private": {
        "ru": "Не могу написать тебе в личку — открой чат со мной и нажми «Старт», потом повтори /export.",
        "en": "I can't message you privately — open a chat with me, tap “Start”, then try /export again.",
    },
    "export_caption": {
        "ru": "📄 Траты и балансы группы «{group}»",
        "en": "📄 Expenses and balances of “{group}”",
    },
    "err_dm_unavailable": {
        "ru": "Не могу написать тебе в личку: открой чат с ботом и нажми «Старт», потом повтори.",
        "en": "I can't message you privately: open the chat with the bot, tap “Start”, then try again.",
    },
    # --- /setpay, /lang ---
    "setpay_prompt": {
        "ru": (
            "💳 Куда тебе переводить долги?\n\n"
            "Возьму номер из твоего профиля Telegram — или введи вручную, если карта на другом номере.\n\n"
            "Сейчас: {current}"
        ),
        "en": (
            "💳 Where should people send you money?\n\n"
            "I can take the phone number from your Telegram profile — or enter it manually.\n\n"
            "Current: {current}"
        ),
    },
    "setpay_none": {"ru": "не указано", "en": "not set"},
    "btn_share_phone": {"ru": "📱 Взять номер из профиля", "en": "📱 Use my Telegram number"},
    "btn_manual_details": {"ru": "✏️ Ввести вручную", "en": "✏️ Enter manually"},
    "btn_cancel": {"ru": "Отмена", "en": "Cancel"},
    "btn_open_app": {"ru": "📱 Открыть приложение", "en": "📱 Open the app"},
    "btn_setpay_private": {"ru": "💳 Мой номер для переводов", "en": "💳 My payment details"},
    "setpay_in_private": {
        "ru": "Номер для переводов удобнее указать в личке — жми кнопку 👇",
        "en": "It's easier to set payment details in a private chat — tap the button 👇",
    },
    "setpay_manual_prompt": {
        "ru": (
            "Пришли номер телефона или карты, куда переводить (до 64 символов). "
            "Например: <code>Kaspi +7 777 123 45 67</code>"
        ),
        "en": "Send the phone or card number to transfer to (up to 64 chars). E.g.: <code>+7 777 123 45 67</code>",
    },
    "setpay_not_own_contact": {
        "ru": "Это чужой контакт 🙂 Нажми кнопку «Взять номер из профиля» или введи номер вручную.",
        "en": "That's someone else's contact 🙂 Tap “Use my Telegram number” or enter it manually.",
    },
    "setpay_cancelled": {"ru": "Ок, ничего не меняю", "en": "OK, nothing changed"},
    "setpay_saved": {
        "ru": "✅ Сохранил: <code>{details}</code>\nТеперь в /settle рядом с тобой будет кнопка «Скопировать».",
        "en": "✅ Saved: <code>{details}</code>\nNow /settle will show a “Copy” button for you.",
    },
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
    "err_no_participants": {"ru": "Выбери хотя бы одного участника", "en": "Pick at least one person"},
    "err_negative_share": {"ru": "Доля не может быть отрицательной", "en": "A share can't be negative"},
    "err_shares_sum": {"ru": "Сумма долей не равна сумме траты", "en": "Shares don't add up to the total"},
    "err_not_member": {"ru": "Этот человек не участвует в группе", "en": "This person is not in the group"},
    "err_not_found": {"ru": "Не найдено", "en": "Not found"},
    "err_unauthorized": {
        "ru": "Открой приложение из Telegram",
        "en": "Please open the app from Telegram",
    },
    "err_category_not_found": {"ru": "Категория не найдена", "en": "Category not found"},
    "err_category_name": {"ru": "Название — от 1 до 32 символов", "en": "Name must be 1–32 characters"},
    "err_category_emoji": {"ru": "Выбери эмодзи", "en": "Pick an emoji"},
    "err_category_limit": {"ru": "Максимум 30 своих категорий", "en": "30 custom categories max"},
    "err_category_exists": {"ru": "Такая категория уже есть", "en": "This category already exists"},
    "err_not_in_chat": {
        "ru": "Ты не состоишь в этом чате Telegram",
        "en": "You're not a member of this Telegram chat",
    },
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
