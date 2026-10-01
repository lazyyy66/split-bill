"""Напоминания должникам.

Раз в N дней (настройка группы), в REMINDER_HOUR по местному времени, бот пишет каждому должнику в личку:
кому и сколько он должен, с кнопками «скопировать реквизиты» и «открыть приложение».
Кому написать нельзя (ни разу не открывал личку с ботом) — попадают в одну сводку в группе.
Переводы, которые уже отмечены и ждут подтверждения, не напоминаем.

Группы «забираются» на отправку атомарным UPDATE ... RETURNING и коммитятся до рассылки:
даже если рассылка упадёт или запущено два экземпляра бота, повторно никто ничего не получит.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.format import mention, money, name, short_name
from app.bot.keyboards import app_button, app_url, copy_button
from app.bot.texts import t
from app.db.models import Group, Settlement, SettlementStatus, User
from app.domain.settlement import Transfer, minimize_transfers
from app.services.balances import group_balances

logger = logging.getLogger(__name__)

REMINDER_INTERVALS = (0, 3, 7)  # 0 — выключены
CHECK_EVERY = timedelta(minutes=10)
# Запас: прошлый раз отправили в 19:05 — через неделю в 19:00 группа уже должна считаться «пора»
SLACK = timedelta(hours=2)


@dataclass
class ReminderStats:
    groups: int = 0
    direct: int = 0  # напоминаний в личку
    group_summaries: int = 0  # сводок в группу — для тех, кому в личку нельзя


async def claim_due_groups(session: AsyncSession, now: datetime) -> list[int]:
    """Отметить группы, которым пора напомнить (last_reminder_at = now), и вернуть их id."""
    last_sent = func.coalesce(Group.last_reminder_at, Group.created_at)
    due_at = last_sent + func.make_interval(0, 0, 0, Group.reminder_interval_days) - SLACK
    result = await session.execute(
        update(Group)
        .where(Group.reminder_interval_days > 0, due_at <= now)
        .values(last_reminder_at=now)
        .returning(Group.id)
    )
    return list(result.scalars())


async def _open_debts(session: AsyncSession, group: Group) -> list[Transfer]:
    rows = await session.execute(
        select(Settlement.from_user_id, Settlement.to_user_id).where(
            Settlement.group_id == group.id, Settlement.status == SettlementStatus.PENDING
        )
    )
    pending = {(from_id, to_id) for from_id, to_id in rows}
    transfers = minimize_transfers(await group_balances(session, group))
    return [tr for tr in transfers if (tr.from_user, tr.to_user) not in pending]


async def send_group_reminders(
    session: AsyncSession, bot: Bot, group: Group, *, short_name_app: str | None = None
) -> ReminderStats:
    stats = ReminderStats(groups=1)
    debts = await _open_debts(session, group)
    if not debts:
        return stats

    ids = {tr.from_user for tr in debts} | {tr.to_user for tr in debts}
    users = {u.id: u for u in await session.scalars(select(User).where(User.id.in_(ids)))}
    me = await bot.me()
    link = app_url(me.username or "", short_name_app, group.public_id) if short_name_app else None

    by_debtor: dict[int, list[Transfer]] = defaultdict(list)
    for tr in debts:
        by_debtor[tr.from_user].append(tr)

    unreachable: list[Transfer] = []
    for debtor_id, transfers in by_debtor.items():
        debtor = users[debtor_id]
        try:
            await bot.send_message(
                debtor.tg_id,
                _dm_text(group, debtor.language, transfers, users),
                reply_markup=_dm_keyboard(group, debtor.language, transfers, users, link),
            )
            stats.direct += 1
        except TelegramForbiddenError, TelegramBadRequest:
            unreachable.extend(transfers)  # личку не открывал или заблокировал бота

    if unreachable:
        lang = group.language
        lines = "\n".join(
            t(
                lang,
                "reminder_group_line",
                debtor=mention(users[tr.from_user]),
                creditor=name(users[tr.to_user]),
                amount=money(group, tr.amount),
            )
            for tr in unreachable
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[app_button(lang, link)]]) if link else None
        try:
            await bot.send_message(group.tg_chat_id, t(lang, "reminder_group", lines=lines), reply_markup=markup)
            stats.group_summaries += 1
        except TelegramForbiddenError, TelegramBadRequest:
            logger.warning("Не удалось отправить сводку напоминаний в группу %s", group.id, exc_info=True)
    return stats


def _dm_text(group: Group, lang: str, transfers: list[Transfer], users: dict[int, User]) -> str:
    lines = []
    for tr in transfers:
        creditor = users[tr.to_user]
        line = t(lang, "reminder_line", name=name(creditor), amount=money(group, tr.amount))
        if creditor.payment_details:
            line += f"\n   <code>{escape(creditor.payment_details)}</code>"
        lines.append(line)
    return t(lang, "reminder_dm", group=escape(group.title), lines="\n".join(lines))


def _dm_keyboard(
    group: Group, lang: str, transfers: list[Transfer], users: dict[int, User], link: str | None
) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for tr in transfers:
        creditor = users[tr.to_user]
        if creditor.payment_details:
            rows.append([copy_button(t(lang, "btn_copy", name=short_name(creditor)), creditor.payment_details)])
    if link:
        rows.append([app_button(lang, link)])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


async def run_due_reminders(
    session_factory: async_sessionmaker[AsyncSession], bot: Bot, now: datetime, *, short_name_app: str | None = None
) -> ReminderStats:
    """Разослать напоминания всем группам, которым пора (без проверки часа — её делает цикл)."""
    async with session_factory() as session, session.begin():
        group_ids = await claim_due_groups(session, now)  # коммитим отметку до рассылки

    total = ReminderStats()
    for group_id in group_ids:
        try:
            async with session_factory() as session:
                group = await session.get(Group, group_id)
                if group is None:
                    continue
                stats = await send_group_reminders(session, bot, group, short_name_app=short_name_app)
        except Exception:
            logger.exception("Ошибка при напоминаниях для группы %s", group_id)
            continue
        total.groups += 1
        total.direct += stats.direct
        total.group_summaries += stats.group_summaries
    return total


async def reminders_loop(
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot,
    *,
    hour: int,
    timezone: str,
    short_name_app: str | None = None,
) -> None:
    """Фоновая задача бота: каждые 10 минут проверяет, не наступил ли час напоминаний."""
    tz = ZoneInfo(timezone)
    while True:
        now = datetime.now(UTC)
        if now.astimezone(tz).hour == hour:
            try:
                stats = await run_due_reminders(session_factory, bot, now, short_name_app=short_name_app)
                if stats.groups:
                    logger.info("Напоминания: %s", stats)
            except Exception:
                logger.exception("Ошибка в цикле напоминаний")
        await asyncio.sleep(CHECK_EVERY.total_seconds())


async def _send_now() -> None:
    """Ручная проверка: разослать напоминания всем группам с включёнными напоминаниями, не дожидаясь срока.

    uv run python -m app.bot.reminders
    """
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from app.config import get_settings
    from app.db.session import create_engine, create_session_factory

    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    async with Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
        async with session_factory() as session, session.begin():
            # сбрасываем «когда напоминали» и считаем группы старыми — тогда все с напоминаниями попадут в рассылку
            await session.execute(update(Group).where(Group.reminder_interval_days > 0).values(last_reminder_at=None))
        far_future = datetime.now(UTC) + timedelta(days=365)
        stats = await run_due_reminders(session_factory, bot, far_future, short_name_app=settings.webapp_short_name)
        async with session_factory() as session, session.begin():
            # отметку ставим реальным временем, а не «через год»
            await session.execute(
                update(Group)
                .where(Group.id.in_(select(Group.id).where(Group.last_reminder_at == far_future)))
                .values(last_reminder_at=datetime.now(UTC))
            )
    await engine.dispose()
    print(f"Групп: {stats.groups}, в личку: {stats.direct}, сводок в группы: {stats.group_summaries}")


if __name__ == "__main__":
    asyncio.run(_send_now())
