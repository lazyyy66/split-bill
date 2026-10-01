"""Запуск бота в режиме polling (локальная разработка): python -m app.bot"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from app.bot.handlers import common, group
from app.bot.middlewares import DbSessionMiddleware
from app.config import get_settings
from app.db.session import create_engine, create_session_factory

GROUP_COMMANDS = {
    "ru": [
        ("add", "Добавить трату: /add 12000 продукты"),
        ("balance", "Кто сколько должен"),
        ("settle", "Как рассчитаться"),
        ("paid", "Отметить перевод: /paid 3000 @user"),
        ("setpay", "Мой номер для переводов"),
        ("start", "Участники и помощь"),
        ("lang", "Язык: /lang ru | en"),
    ],
    "en": [
        ("add", "Add expense: /add 12000 groceries"),
        ("balance", "Who owes what"),
        ("settle", "How to settle up"),
        ("paid", "Record a transfer: /paid 3000 @user"),
        ("setpay", "My payment details"),
        ("start", "Members and help"),
        ("lang", "Language: /lang ru | en"),
    ],
}
PRIVATE_COMMANDS = {
    "ru": [("setpay", "Мой номер для переводов"), ("lang", "Язык: /lang ru | en")],
    "en": [("setpay", "My payment details"), ("lang", "Language: /lang ru | en")],
}


async def set_commands(bot: Bot) -> None:
    for lang in ("ru", "en"):
        language_code = lang if lang == "ru" else None  # en — по умолчанию для всех остальных языков
        for scope, commands in (
            (BotCommandScopeAllGroupChats(), GROUP_COMMANDS[lang]),
            (BotCommandScopeAllPrivateChats(), PRIVATE_COMMANDS[lang]),
        ):
            await bot.set_my_commands(
                [BotCommand(command=c, description=d) for c, d in commands],
                scope=scope,
                language_code=language_code,
            )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    engine = create_engine(settings.database_url)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(create_session_factory(engine)))
    dp.include_routers(common.router, group.router)

    await set_commands(bot)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
