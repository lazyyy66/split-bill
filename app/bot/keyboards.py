from aiogram.filters.callback_data import CallbackData
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.texts import t

# /start-параметр ссылки t.me/<bot>?start=setpay — открывает настройку реквизитов в личке
SETPAY_START_PAYLOAD = "setpay"


def setpay_url(bot_username: str) -> str:
    return f"https://t.me/{bot_username}?start={SETPAY_START_PAYLOAD}"


class JoinCb(CallbackData, prefix="join"):
    pass


class ExpenseCb(CallbackData, prefix="exp"):
    action: str  # "del"
    expense_id: int


class PayCb(CallbackData, prefix="pay"):
    """Кнопка «я перевёл» под /settle. id — внутренние users.id, amount — в минимальных единицах."""

    from_id: int
    to_id: int
    amount: int


class SettlementCb(CallbackData, prefix="stl"):
    settlement_id: int
    confirm: bool


def join_kb(lang: str, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_join"), callback_data=JoinCb().pack())],
            [InlineKeyboardButton(text=t(lang, "btn_setpay_private"), url=setpay_url(bot_username))],
        ]
    )


def setpay_link_kb(lang: str, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_setpay_private"), url=setpay_url(bot_username))]]
    )


def expense_kb(lang: str, expense_id: int) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(
        text=t(lang, "btn_cancel_expense"), callback_data=ExpenseCb(action="del", expense_id=expense_id).pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def pay_button(text: str, from_id: int, to_id: int, amount: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=PayCb(from_id=from_id, to_id=to_id, amount=amount).pack())


def copy_button(text: str, value: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, copy_text=CopyTextButton(text=value))


def settlement_kb(lang: str, settlement_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_confirm"),
                    callback_data=SettlementCb(settlement_id=settlement_id, confirm=True).pack(),
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_reject"),
                    callback_data=SettlementCb(settlement_id=settlement_id, confirm=False).pack(),
                ),
            ]
        ]
    )
