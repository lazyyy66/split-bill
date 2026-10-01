from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, Expense, ExpenseAction, ExpenseHistory, ExpenseShare, Group, User
from app.domain.settlement import split_equal


class ExpenseError(Exception):
    pass


def _snapshot(expense: Expense) -> dict[str, Any]:
    return {
        "amount": expense.amount,
        "title": expense.title,
        "payer_id": expense.payer_id,
        "category_id": expense.category_id,
        "shares": {str(s.user_id): s.amount for s in expense.shares},
    }


async def get_system_category(session: AsyncSession, code: str) -> Category:
    category = await session.scalar(select(Category).where(Category.code == code))
    if category is None:
        raise ExpenseError(f"Нет системной категории {code!r} — применены ли миграции?")
    return category


async def add_expense(
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
    """Трата, поделённая поровну между participants."""
    if not participants:
        raise ExpenseError("Не на кого делить трату")

    shares = split_equal(amount, [u.id for u in participants], payer_id=payer.id)
    expense = Expense(
        group_id=group.id,
        payer_id=payer.id,
        amount=amount,
        title=title,
        category_id=category.id,
        created_by=created_by.id,
        shares=[ExpenseShare(user_id=user_id, amount=share) for user_id, share in shares.items()],
    )
    session.add(expense)
    await session.flush()

    session.add(
        ExpenseHistory(
            expense_id=expense.id, user_id=created_by.id, action=ExpenseAction.CREATE, snapshot=_snapshot(expense)
        )
    )
    await session.flush()
    return expense


async def get_expense(session: AsyncSession, group: Group, expense_id: int) -> Expense | None:
    return await session.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.group_id == group.id, Expense.deleted_at.is_(None))
    )


async def delete_expense(session: AsyncSession, expense: Expense, by: User) -> None:
    """Мягкое удаление: трата пропадает из балансов, но остаётся в истории."""
    expense.deleted_at = datetime.now(UTC)
    session.add(
        ExpenseHistory(expense_id=expense.id, user_id=by.id, action=ExpenseAction.DELETE, snapshot=_snapshot(expense))
    )
    await session.flush()
