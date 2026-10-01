"""Сборка диспетчера — общая для запуска бота и e2e-тестов."""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import common, group
from app.bot.middlewares import DbSessionMiddleware


def create_dispatcher(
    session_factory: async_sessionmaker[AsyncSession], storage: BaseStorage, *, webapp_short_name: str | None = None
) -> Dispatcher:
    """webapp_short_name — короткое имя Mini App из BotFather; без него кнопки «Открыть приложение» нет."""
    dp = Dispatcher(storage=storage, webapp_short_name=webapp_short_name)
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.include_routers(common.router, group.router)
    return dp


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
