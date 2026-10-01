"""Напоминания должникам: кому в личку, кому сводкой в группу, как часто."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.reminders import run_due_reminders
from app.db.models import Group
from app.db.session import create_session_factory
from tests.integration.tg import TgHarness, buttons

WEEK_LATER = datetime.now(UTC) + timedelta(days=8)


@pytest.fixture
async def trip(tg: TgHarness):
    """Роман заплатил 9000 за троих: Арман и Даша должны ему по 3000. Арман открывал личку с ботом, Даша — нет."""
    roman, arman, dasha = tg.person("Роман", "roman"), tg.person("Арман", "arman"), tg.person("Даша", "dasha")
    chat = tg.group()
    [welcome] = await tg.add_bot_to_group(chat, by=roman)
    for person in (arman, dasha):
        await person.click(welcome, "Я в деле")
    await roman.send(roman.private_chat, "/setpay Kaspi +7 777 123 45 67")
    await arman.send(arman.private_chat, "/start")
    await roman.send(chat, "/add 9000 ужин")
    tg.telegram.reset()
    return chat, roman, arman, dasha


async def remind(tg: TgHarness, engine: AsyncEngine, now: datetime = WEEK_LATER):
    return await run_due_reminders(create_session_factory(engine), tg.bot, now, short_name_app="app")


async def test_debtor_with_private_chat_gets_dm(tg: TgHarness, engine: AsyncEngine, trip):
    chat, roman, arman, dasha = trip
    stats = await remind(tg, engine)
    assert (stats.groups, stats.direct, stats.group_summaries) == (1, 1, 1)

    [dm] = [m for m in tg.telegram.sent if m.chat.id == arman.tg.id]
    assert "Напоминание" in dm.text
    assert "Роман" in dm.text and "3 000 ₸" in dm.text
    assert "Kaspi +7 777 123 45 67" in dm.text
    copy = [b for b in buttons(dm.reply_markup) if b.copy_text]
    assert copy and copy[0].copy_text.text == "Kaspi +7 777 123 45 67"
    assert any(b.url and "startapp=g_" in b.url for b in buttons(dm.reply_markup))


async def test_debtor_without_private_chat_is_reminded_in_group(tg: TgHarness, engine: AsyncEngine, trip):
    chat, roman, arman, dasha = trip
    await remind(tg, engine)

    [summary] = [m for m in tg.telegram.sent if m.chat.id == chat.id]
    assert "Напоминание о долгах" in summary.text
    assert "Даша" in summary.text
    assert "Арман" not in summary.text  # ему уже написали в личку
    # кредитору ничего не приходит
    assert not [m for m in tg.telegram.sent if m.chat.id == roman.tg.id]


async def test_not_sent_twice_and_respects_interval(tg: TgHarness, engine: AsyncEngine, trip):
    await remind(tg, engine)
    assert (await remind(tg, engine)).groups == 0  # то же время — уже отправлено
    assert (await remind(tg, engine, WEEK_LATER + timedelta(days=3))).groups == 0  # раз в неделю, а прошло 3 дня
    assert (await remind(tg, engine, WEEK_LATER + timedelta(days=7))).groups == 1


async def test_fresh_group_is_not_reminded_immediately(tg: TgHarness, engine: AsyncEngine, trip):
    assert (await remind(tg, engine, datetime.now(UTC))).groups == 0


async def test_every_three_days_and_off(tg: TgHarness, engine: AsyncEngine, trip):
    async with engine.begin() as conn:
        await conn.execute(update(Group).values(reminder_interval_days=3))
    assert (await remind(tg, engine, datetime.now(UTC) + timedelta(days=3))).groups == 1

    async with engine.begin() as conn:
        await conn.execute(update(Group).values(reminder_interval_days=0))
    assert (await remind(tg, engine, datetime.now(UTC) + timedelta(days=30))).groups == 0


async def test_pending_transfer_is_not_reminded(tg: TgHarness, engine: AsyncEngine, trip):
    chat, roman, arman, dasha = trip
    await arman.send(chat, "/paid 3000 @roman")  # ждёт подтверждения Романа
    tg.telegram.reset()

    stats = await remind(tg, engine)
    assert stats.direct == 0  # Арману не напоминаем — он уже отметил перевод
    assert stats.group_summaries == 1  # а Даше — да


async def test_settled_group_gets_nothing(tg: TgHarness, engine: AsyncEngine, trip):
    chat, roman, arman, dasha = trip
    for person in (arman, dasha):
        [request] = await person.send(chat, "/paid 3000 @roman")
        await roman.click(request, "Получил")
    tg.telegram.reset()

    stats = await remind(tg, engine)
    assert stats.groups == 1 and stats.direct == 0 and stats.group_summaries == 0
    assert tg.telegram.sent == []


async def test_dm_in_debtor_language(tg: TgHarness, engine: AsyncEngine, trip):
    chat, roman, arman, dasha = trip
    await arman.send(arman.private_chat, "/lang en")
    tg.telegram.reset()
    await remind(tg, engine)
    [dm] = [m for m in tg.telegram.sent if m.chat.id == arman.tg.id]
    assert "Reminder from" in dm.text and "You owe" in dm.text
