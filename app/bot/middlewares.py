from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Chat, TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.groups import get_group, upsert_user

GROUP_CHAT_TYPES = {"group", "supergroup"}


class DbSessionMiddleware(BaseMiddleware):
    """Одна транзакция на апдейт. Кладёт в хендлеры: session, user, group, lang.

    user — наш User (или None для ботов/каналов), group — наша Group, если апдейт из
    уже известного группового чата.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session, session.begin():
            tg_user: TgUser | None = data.get("event_from_user")
            chat: Chat | None = data.get("event_chat")

            user = None
            if tg_user is not None and not tg_user.is_bot:
                user = await upsert_user(
                    session, tg_user.id, tg_user.full_name, tg_user.username, tg_user.language_code
                )

            group = None
            if chat is not None and chat.type in GROUP_CHAT_TYPES:
                group = await get_group(session, chat.id)

            data["session"] = session
            data["user"] = user
            data["group"] = group
            data["lang"] = group.language if group else (user.language if user else "ru")
            return await handler(event, data)
