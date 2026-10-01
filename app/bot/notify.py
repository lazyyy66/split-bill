"""Сообщения бота в группу о событиях, которые произошли в Mini App (и общие с хендлерами).

Ошибка Telegram (бота выгнали из чата, сеть) не должна ломать действие пользователя —
поэтому всё отправляется через _safe: ошибка логируется, данные в БД уже сохранены.
"""

import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.format import expense_text, money, name, settlement_text
from app.bot.keyboards import expense_kb, settlement_kb
from app.bot.texts import t
from app.db.models import Expense, Group, Settlement, SettlementStatus, User
from app.services.export import build_export, export_filename

logger = logging.getLogger(__name__)


async def _safe[T](call: Awaitable[T]) -> T | None:
    try:
        return await call
    except TelegramAPIError:
        logger.warning("Не удалось отправить сообщение в Telegram", exc_info=True)
        return None


async def expense_added(bot: Bot, group: Group, expense: Expense, by: User) -> None:
    text = expense_text(group, expense, added_by=by)
    await _safe(bot.send_message(group.tg_chat_id, text, reply_markup=expense_kb(group.language, expense.id)))


async def expense_deleted(bot: Bot, group: Group, expense: Expense, by: User) -> None:
    text = t(
        group.language,
        "expense_deleted",
        title=escape(expense.title),
        amount=money(group, expense.amount),
        by=name(by),
    )
    await _safe(bot.send_message(group.tg_chat_id, text))


async def settlement_requested(bot: Bot, group: Group, settlement: Settlement) -> None:
    """«Арман перевёл Роману 3 000 ₸, подтверди 👇» — запоминаем id сообщения, чтобы потом обновить."""
    sent = await _safe(
        bot.send_message(
            group.tg_chat_id,
            settlement_text(group, settlement),
            reply_markup=settlement_kb(group.language, settlement.id),
        )
    )
    if isinstance(sent, Message):
        settlement.tg_message_id = sent.message_id


async def settlement_resolved(bot: Bot, group: Group, settlement: Settlement) -> None:
    """Подтвердили/отклонили в Mini App — убираем кнопки у сообщения в чате."""
    assert settlement.status != SettlementStatus.PENDING
    if settlement.tg_message_id is None:
        return
    await _safe(
        bot.edit_message_text(
            settlement_text(group, settlement), chat_id=group.tg_chat_id, message_id=settlement.tg_message_id
        )
    )


async def send_export(bot: Bot, session: AsyncSession, group: Group, user: User, *, timezone: str) -> bool:
    """Прислать Excel-файл группы в личку. False — если личка с ботом не открыта (бот не может написать первым)."""
    data = await build_export(session, group, timezone=timezone)
    filename = export_filename(group, datetime.now(UTC))
    caption = t(user.language, "export_caption", group=escape(group.title))
    try:
        await bot.send_document(user.tg_id, BufferedInputFile(data, filename=filename), caption=caption)
    except TelegramForbiddenError, TelegramBadRequest:
        return False
    return True
