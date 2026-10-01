"""Запуск бота в режиме polling (локальная разработка): python -m app.bot"""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.factory import create_dispatcher, set_commands
from app.bot.reminders import reminders_loop
from app.config import get_settings
from app.db.session import create_engine, create_session_factory


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    engine = create_engine(settings.database_url)
    storage = RedisStorage.from_url(settings.redis_url)  # состояния диалогов переживают перезапуск бота
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(
        create_session_factory(engine),
        storage,
        webapp_short_name=settings.webapp_short_name,
        timezone=settings.timezone,
    )

    await set_commands(bot)
    reminders = asyncio.create_task(
        reminders_loop(
            create_session_factory(engine),
            bot,
            hour=settings.reminder_hour,
            timezone=settings.timezone,
            short_name_app=settings.webapp_short_name,
        )
    )
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminders.cancel()
        await storage.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
