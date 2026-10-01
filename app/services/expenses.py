from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, Expense, ExpenseAction, ExpenseHistory, ExpenseShare, Group, User
from app.domain.settlement import split_equal
from app.services.groups import active_member_ids

MAX_TITLE = 128
MAX_CUSTOM_CATEGORIES = 30
MAX_CATEGORY_NAME = 32


class ExpenseError(Exception):
    """args[0] — ключ текста ошибки (err_*) из app/bot/texts.py; API отдаёт его клиенту как code."""


class ExpenseConflictError(ExpenseError):
    """Трату изменили, пока пользователь её редактировал (оптимистичная блокировка)."""

    def __init__(self) -> None:
        super().__init__("err_conflict")


def _snapshot(expense: Expense) -> dict[str, Any]:
    return {
        "amount": expense.amount,
        "title": expense.title,
        "payer_id": expense.payer_id,
        "category_id": expense.category_id,
        "shares": {str(s.user_id): s.amount for s in expense.shares},
    }


def validate_shares(amount: int, shares: dict[int, int], allowed_user_ids: set[int]) -> None:
    if amount <= 0:
        raise ExpenseError("err_amount")
    if not shares or all(v == 0 for v in shares.values()):
        raise ExpenseError("err_no_participants")
    if any(v < 0 for v in shares.values()):
        raise ExpenseError("err_negative_share")
    if sum(shares.values()) != amount:
        raise ExpenseError("err_shares_sum")
    if not set(shares) <= allowed_user_ids:
        raise ExpenseError("err_not_member")


# --- категории ---


async def get_system_category(session: AsyncSession, code: str) -> Category:
    category = await session.scalar(select(Category).where(Category.code == code))
    if category is None:
        raise ExpenseError(f"Нет системной категории {code!r} — применены ли миграции?")
    return category


async def list_categories(session: AsyncSession, group: Group) -> list[Category]:
    """Системные (в порядке создания) + свои категории группы."""
    query = (
        select(Category)
        .where(or_(Category.group_id.is_(None), Category.group_id == group.id))
        .order_by(Category.group_id.is_not(None), Category.id)
    )
    return list(await session.scalars(query))


async def get_category(session: AsyncSession, group: Group, category_id: int) -> Category:
    category = await session.get(Category, category_id)
    if category is None or category.group_id not in (None, group.id):
        raise ExpenseError("err_category_not_found")
    return category


async def create_category(session: AsyncSession, group: Group, name: str, emoji: str) -> Category:
    name, emoji = name.strip(), emoji.strip()
    if not name or len(name) > MAX_CATEGORY_NAME:
        raise ExpenseError("err_category_name")
    if not emoji or len(emoji) > 8:
        raise ExpenseError("err_category_emoji")

    count = await session.scalar(select(func.count()).where(Category.group_id == group.id))
    if (count or 0) >= MAX_CUSTOM_CATEGORIES:
        raise ExpenseError("err_category_limit")
    exists = await session.scalar(
        select(Category.id).where(Category.group_id == group.id, func.lower(Category.name) == name.lower())
    )
    if exists:
        raise ExpenseError("err_category_exists")

    category = Category(group_id=group.id, name=name, emoji=emoji)
    session.add(category)
    await session.flush()
    return category


# --- траты ---


async def add_expense(
    session: AsyncSession,
    *,
    group: Group,
    payer_id: int,
    amount: int,
    title: str,
    category: Category,
    shares: dict[int, int],
    created_by: User,
) -> Expense:
    """Трата с произвольными долями (сумма долей = amount). Плательщик и участники — активные члены группы."""
    members = await active_member_ids(session, group)
    validate_shares(amount, shares, members)
    if payer_id not in members:
        raise ExpenseError("err_not_member")

    expense = Expense(
        group_id=group.id,
        payer_id=payer_id,
        amount=amount,
        title=title.strip()[:MAX_TITLE],
        category_id=category.id,
        created_by=created_by.id,
        shares=[ExpenseShare(user_id=user_id, amount=share) for user_id, share in shares.items() if share > 0],
    )
    session.add(expense)
    await session.flush()
    await session.refresh(expense, ["payer", "category", "shares"])  # с именами участников для сообщений

    session.add(
        ExpenseHistory(
            expense_id=expense.id, user_id=created_by.id, action=ExpenseAction.CREATE, snapshot=_snapshot(expense)
        )
    )
    await session.flush()
    return expense


async def add_equal_expense(
    session: AsyncSession,
    *,
    group: Group,
    payer: User,
    amount: int,
    title: str,
    category: Category,
    participants: Sequence[User],
    created_by: User,
) -> Expense:
    """Трата, поделённая поровну (остаток — плательщику)."""
    if not participants:
        raise ExpenseError("err_no_participants")
    shares = split_equal(amount, [u.id for u in participants], payer_id=payer.id)
    return await add_expense(
        session,
        group=group,
        payer_id=payer.id,
        amount=amount,
        title=title,
        category=category,
        shares=shares,
        created_by=created_by,
    )


async def update_expense(
    session: AsyncSession,
    expense: Expense,
    *,
    version: int,
    by: User,
    payer_id: int,
    amount: int,
    title: str,
    category: Category,
    shares: dict[int, int],
) -> Expense:
    """Редактирование с оптимистичной блокировкой: version — та, что видел пользователь."""
    if expense.version != version:
        raise ExpenseConflictError

    # Уже участвующих оставляем допустимыми, даже если они вышли из чата
    allowed = await active_member_ids(session, expense.group_id) | {s.user_id for s in expense.shares}
    validate_shares(amount, shares, allowed)
    if payer_id not in allowed | {expense.payer_id}:
        raise ExpenseError("err_not_member")

    expense.payer_id = payer_id
    expense.amount = amount
    expense.title = title.strip()[:MAX_TITLE]
    expense.category_id = category.id

    # Доли обновляем на месте: удалить и вставить заново строку с тем же (expense_id, user_id)
    # в одном flush нельзя — SQLAlchemy выполнит INSERT раньше DELETE
    current = {s.user_id: s for s in expense.shares}
    for user_id, share in list(current.items()):
        if shares.get(user_id, 0) == 0:
            expense.shares.remove(share)
    for user_id, amount_ in shares.items():
        if amount_ == 0:
            continue
        if user_id in current:
            current[user_id].amount = amount_
        else:
            expense.shares.append(ExpenseShare(user_id=user_id, amount=amount_))

    await session.flush()
    await session.refresh(expense, ["payer", "category", "shares"])  # с именами участников для сообщений
    session.add(
        ExpenseHistory(expense_id=expense.id, user_id=by.id, action=ExpenseAction.UPDATE, snapshot=_snapshot(expense))
    )
    await session.flush()
    return expense


async def get_expense(session: AsyncSession, group: Group, expense_id: int) -> Expense | None:
    return await session.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.group_id == group.id, Expense.deleted_at.is_(None))
    )


async def list_expenses(
    session: AsyncSession, group: Group, *, limit: int = 30, before_id: int | None = None
) -> list[Expense]:
    """Новые сверху. Пагинация курсором before_id — стабильна, когда добавляются новые траты."""
    query = select(Expense).where(Expense.group_id == group.id, Expense.deleted_at.is_(None))
    if before_id is not None:
        query = query.where(Expense.id < before_id)
    return list(await session.scalars(query.order_by(Expense.id.desc()).limit(limit)))


async def expense_history(session: AsyncSession, expense: Expense) -> list[ExpenseHistory]:
    query = select(ExpenseHistory).where(ExpenseHistory.expense_id == expense.id).order_by(ExpenseHistory.id)
    return list(await session.scalars(query))


async def delete_expense(session: AsyncSession, expense: Expense, by: User, *, version: int | None = None) -> None:
    """Мягкое удаление: трата пропадает из балансов, но остаётся в истории."""
    if version is not None and expense.version != version:
        raise ExpenseConflictError
    expense.deleted_at = datetime.now(UTC)
    session.add(
        ExpenseHistory(expense_id=expense.id, user_id=by.id, action=ExpenseAction.DELETE, snapshot=_snapshot(expense))
    )
    await session.flush()
