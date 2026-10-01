from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Group, GroupMember, User


def detect_language(language_code: str | None) -> str:
    """Telegram language_code → язык бота. Для СНГ — русский, иначе английский."""
    if language_code and language_code.split("-")[0] in {"ru", "uk", "be", "kk", "uz", "ky"}:
        return "ru"
    return "en"


async def upsert_user(
    session: AsyncSession, tg_id: int, name: str, username: str | None, language_code: str | None
) -> User:
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if user is None:
        user = User(tg_id=tg_id, name=name, username=username, language=detect_language(language_code))
        session.add(user)
    else:
        # имя и username в Telegram могут меняться — держим актуальными
        user.name = name
        user.username = username
    await session.flush()
    return user


async def get_or_create_group(session: AsyncSession, tg_chat_id: int, title: str, language: str) -> Group:
    group = await session.scalar(select(Group).where(Group.tg_chat_id == tg_chat_id))
    if group is None:
        group = Group(tg_chat_id=tg_chat_id, title=title, language=language)
        session.add(group)
    else:
        group.title = title
    await session.flush()
    return group


async def get_group(session: AsyncSession, tg_chat_id: int) -> Group | None:
    return await session.scalar(select(Group).where(Group.tg_chat_id == tg_chat_id))


async def ensure_member(session: AsyncSession, group: Group, user: User) -> bool:
    """Добавляет пользователя в группу (или возвращает вышедшего). True — если он новый/вернулся."""
    member = await session.get(GroupMember, (group.id, user.id))
    if member is None:
        session.add(GroupMember(group_id=group.id, user_id=user.id))
        await session.flush()
        return True
    if member.left_at is not None:
        member.left_at = None
        await session.flush()
        return True
    return False


async def mark_left(session: AsyncSession, group: Group, user: User) -> None:
    member = await session.get(GroupMember, (group.id, user.id))
    if member is not None and member.left_at is None:
        member.left_at = datetime.now(UTC)
        await session.flush()


async def list_members(session: AsyncSession, group: Group, *, include_left: bool = False) -> list[GroupMember]:
    query = select(GroupMember).where(GroupMember.group_id == group.id).order_by(GroupMember.joined_at)
    if not include_left:
        query = query.where(GroupMember.left_at.is_(None))
    return list(await session.scalars(query))


async def find_member_by_username(session: AsyncSession, group: Group, username: str) -> User | None:
    username = username.removeprefix("@").lower()
    return await session.scalar(
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group.id, func.lower(User.username) == username)
    )
