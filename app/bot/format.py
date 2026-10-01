"""Форматирование сообщений бота — общее для хендлеров и уведомлений из API."""

from html import escape

from app.bot.texts import t
from app.db.models import Expense, Group, Settlement, SettlementStatus, User
from app.domain.money import CURRENCIES, format_amount


def mention(user: User) -> str:
    """Кликабельное имя — Telegram пришлёт человеку уведомление."""
    return f'<a href="tg://user?id={user.tg_id}">{escape(user.name)}</a>'


def name(user: User) -> str:
    return escape(user.name)


def short_name(user: User, limit: int = 12) -> str:
    first = user.name.split()[0] if user.name.split() else user.name
    return first if len(first) <= limit else first[: limit - 1] + "…"


def money(group: Group, amount: int) -> str:
    return format_amount(amount, CURRENCIES[group.currency], group.language)


def expense_text(group: Group, expense: Expense, *, added_by: User | None = None) -> str:
    """🍽 <b>Ужин</b> — 9 000 ₸ / Платил(а): Роман / Делим на 3: по 3 000 ₸ (или список долей)."""
    lang = group.language
    shares = sorted(expense.shares, key=lambda s: -s.amount)
    count = len(shares)
    equal = max(s.amount for s in shares) - min(s.amount for s in shares) <= 1
    if equal:
        per_key = "per_person_equal" if expense.amount % count == 0 else "per_person_about"
        split = t(lang, per_key, amount=money(group, expense.amount // count))
    else:
        split = ", ".join(f"{name(s.user)} {money(group, s.amount)}" for s in shares)

    text = t(
        lang,
        "expense_added",
        emoji=expense.category.emoji,
        title=escape(expense.title),
        amount=money(group, expense.amount),
        payer=name(expense.payer),
        count=count,
        per_person=split,
    )
    if added_by is not None and added_by.id != expense.payer_id:
        text += "\n" + t(lang, "expense_added_by", by=name(added_by))
    return text


def settlement_text(group: Group, settlement: Settlement) -> str:
    lang = group.language
    amount = money(group, settlement.amount)
    match settlement.status:
        case SettlementStatus.CONFIRMED:
            key = "settlement_confirmed"
        case SettlementStatus.REJECTED:
            key = "settlement_rejected"
        case _:
            return t(
                lang,
                "settlement_pending",
                debtor=name(settlement.from_user),
                creditor=mention(settlement.to_user),
                amount=amount,
            )
    return t(lang, key, debtor=name(settlement.from_user), creditor=name(settlement.to_user), amount=amount)
