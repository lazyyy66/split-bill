"""Команды, которые работают и в личке, и в группе."""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.bot.texts import LANGUAGES, t
from app.db.models import Group, User

router = Router(name="common")
router.message.filter(F.from_user, ~F.from_user.is_bot)

MAX_PAYMENT_DETAILS = 64


@router.message(CommandStart(), F.chat.type == "private")
@router.message(Command("help"), F.chat.type == "private")
async def private_start(message: Message, lang: str) -> None:
    await message.answer(t(lang, "private_start"))


@router.message(Command("setpay"))
async def cmd_setpay(message: Message, command: CommandObject, user: User, lang: str) -> None:
    details = (command.args or "").strip()
    if not details:
        current = escape(user.payment_details) if user.payment_details else t(lang, "setpay_none")
        await message.reply(t(lang, "setpay_usage", current=current))
        return
    if len(details) > MAX_PAYMENT_DETAILS:
        await message.reply(t(lang, "setpay_too_long"))
        return

    user.payment_details = details
    await message.reply(t(lang, "setpay_saved", details=escape(details)))


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
