"""Команды для лички и группы: реквизиты для переводов, язык, /start в личке.

Реквизиты указываются в личке: только там Telegram умеет отдать номер из профиля
(кнопка request_contact). В группе /setpay присылает ссылку в личку.
"""

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.bot.keyboards import SETPAY_START_PAYLOAD, setpay_link_kb
from app.bot.texts import LANGUAGES, TEXTS, t
from app.db.models import Group, User
from app.domain.phone import format_phone

router = Router(name="common")
router.message.filter(F.from_user, ~F.from_user.is_bot)

MAX_PAYMENT_DETAILS = 64
PRIVATE = F.chat.type == "private"


class PaymentDetails(StatesGroup):
    choosing = State()  # показаны кнопки «из профиля» / «вручную»
    manual = State()  # ждём текст с номером


def _button_texts(key: str) -> set[str]:
    return set(TEXTS[key].values())


def _setpay_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)],
            [KeyboardButton(text=t(lang, "btn_manual_details")), KeyboardButton(text=t(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _save_details(message: Message, state: FSMContext, user: User, lang: str, details: str) -> None:
    if len(details) > MAX_PAYMENT_DETAILS:
        await message.answer(t(lang, "setpay_too_long"))
        return
    user.payment_details = details
    await state.clear()
    await message.answer(t(lang, "setpay_saved", details=escape(details)), reply_markup=ReplyKeyboardRemove())


async def _ask_payment_details(message: Message, state: FSMContext, user: User, lang: str) -> None:
    current = f"<code>{escape(user.payment_details)}</code>" if user.payment_details else t(lang, "setpay_none")
    await state.set_state(PaymentDetails.choosing)
    await message.answer(t(lang, "setpay_prompt", current=current), reply_markup=_setpay_keyboard(lang))


# --- /start в личке ---


@router.message(CommandStart(deep_link=True, magic=F.args == SETPAY_START_PAYLOAD), PRIVATE)
async def start_setpay(message: Message, state: FSMContext, user: User, lang: str) -> None:
    """Пришли по ссылке «💳 Мой номер для переводов» из группы."""
    await _ask_payment_details(message, state, user, lang)


@router.message(CommandStart(), PRIVATE)
@router.message(Command("help"), PRIVATE)
async def private_start(message: Message, lang: str) -> None:
    await message.answer(t(lang, "private_start"))


# --- реквизиты ---


@router.message(Command("setpay"))
async def cmd_setpay(
    message: Message, command: CommandObject, state: FSMContext, bot: Bot, user: User, lang: str
) -> None:
    details = (command.args or "").strip()
    if details:  # быстрый путь: /setpay Kaspi +7 777 ...
        await _save_details(message, state, user, lang, details)
        return
    if message.chat.type != "private":
        me = await bot.me()
        await message.reply(t(lang, "setpay_in_private"), reply_markup=setpay_link_kb(lang, me.username or ""))
        return
    await _ask_payment_details(message, state, user, lang)


@router.message(PRIVATE, F.contact)
async def on_contact(message: Message, state: FSMContext, user: User, lang: str) -> None:
    contact = message.contact
    assert contact is not None
    # Через скрепку можно прислать чужой контакт — берём только свой
    if contact.user_id != user.tg_id:
        await message.answer(t(lang, "setpay_not_own_contact"))
        return
    await _save_details(message, state, user, lang, format_phone(contact.phone_number))


@router.message(PRIVATE, StateFilter(PaymentDetails), F.text.in_(_button_texts("btn_cancel")))
async def on_cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "setpay_cancelled"), reply_markup=ReplyKeyboardRemove())


@router.message(PRIVATE, StateFilter(PaymentDetails.choosing), F.text.in_(_button_texts("btn_manual_details")))
async def on_manual_chosen(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(PaymentDetails.manual)
    await message.answer(t(lang, "setpay_manual_prompt"), reply_markup=ReplyKeyboardRemove())


@router.message(PRIVATE, StateFilter(PaymentDetails.manual), F.text, ~F.text.startswith("/"))
async def on_manual_details(message: Message, state: FSMContext, user: User, lang: str) -> None:
    assert message.text is not None
    await _save_details(message, state, user, lang, message.text.strip())


# --- язык ---


@router.message(Command("lang"))
async def cmd_lang(message: Message, command: CommandObject, user: User, group: Group | None, lang: str) -> None:
    new_lang = (command.args or "").strip().lower()
    if new_lang not in LANGUAGES:
        await message.reply(t(lang, "lang_usage"))
        return

    if group is not None:
        group.language = new_lang
    else:
        user.language = new_lang
    await message.reply(t(new_lang, "lang_set"))
