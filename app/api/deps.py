from collections.abc import AsyncIterator
from typing import Annotated

from aiogram import Bot
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.api.init_data import InitDataError, validate_init_data
from app.config import Settings
from app.db.models import Group, User
from app.services.groups import get_group_by_public_id, is_active_member, upsert_user


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_bot(request: Request) -> Bot:
    return request.app.state.bot


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Сессия на запрос. Изменения эндпоинты коммитят явно (session.commit), иначе — откат."""
    async with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
BotDep = Annotated[Bot, Depends(get_bot)]


async def current_user(
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Пользователь из подписанного initData: заголовок `Authorization: tma <initData>`.

    user_id из тела запроса или query никогда не используется — только отсюда.
    """
    scheme, _, raw = (authorization or "").partition(" ")
    if scheme.lower() != "tma" or not raw:
        raise ApiError(401, "err_unauthorized")
    try:
        data = validate_init_data(raw, settings.bot_token)
    except InitDataError:
        raise ApiError(401, "err_unauthorized") from None

    tg = data.user
    user = await upsert_user(session, tg.id, tg.full_name, tg.username, tg.language_code)
    await session.commit()
    request.state.lang = user.language
    return user


UserDep = Annotated[User, Depends(current_user)]


async def any_group(public_id: str, session: SessionDep, user: UserDep) -> Group:
    """Группа по public_id — без проверки членства (для экрана «присоединиться»)."""
    group = await get_group_by_public_id(session, public_id)
    if group is None:
        raise ApiError(404, "err_not_found")
    return group


async def member_group(group: Annotated[Group, Depends(any_group)], session: SessionDep, user: UserDep) -> Group:
    """Группа, где пользователь сейчас в деле. Чужие данные не отдаём."""
    if not await is_active_member(session, group, user):
        raise ApiError(403, "members_only")
    return group


AnyGroupDep = Annotated[Group, Depends(any_group)]
GroupDep = Annotated[Group, Depends(member_group)]
