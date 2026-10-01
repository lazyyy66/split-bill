from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Expense, ExpenseShare, Group, Settlement, SettlementStatus, User
from app.domain.settlement import Transfer, minimize_transfers


class SettlementError(Exception):
    """args[0] — ключ текста ошибки из app/bot/texts.py."""


async def group_balances(session: AsyncSession, group: Group) -> dict[int, int]:
    """Чистый баланс каждого участника (users.id → сумма): > 0 — ему должны, < 0 — должен он.

    Считается агрегатами в БД: заплатил − его доли + отправленные переводы − полученные.
    """
    balances: dict[int, int] = {}

    def add(rows, sign: int) -> None:
        for user_id, total in rows:
            balances[user_id] = balances.get(user_id, 0) + sign * int(total)

    active = (Expense.group_id == group.id, Expense.deleted_at.is_(None))
    add(
        await session.execute(
            select(Expense.payer_id, func.sum(Expense.amount)).where(*active).group_by(Expense.payer_id)
        ),
        +1,
    )
    add(
        await session.execute(
            select(ExpenseShare.user_id, func.sum(ExpenseShare.amount))
            .join(Expense)
            .where(*active)
            .group_by(ExpenseShare.user_id)
        ),
        -1,
    )

    confirmed = (Settlement.group_id == group.id, Settlement.status == SettlementStatus.CONFIRMED)
    add(
        await session.execute(
            select(Settlement.from_user_id, func.sum(Settlement.amount))
            .where(*confirmed)
            .group_by(Settlement.from_user_id)
        ),
        +1,
    )
    add(
        await session.execute(
            select(Settlement.to_user_id, func.sum(Settlement.amount)).where(*confirmed).group_by(Settlement.to_user_id)
        ),
        -1,
    )
    return balances


async def suggested_transfers(session: AsyncSession, group: Group) -> list[Transfer]:
    return minimize_transfers(await group_balances(session, group))


async def create_settlement(
    session: AsyncSession, *, group: Group, from_user: User, to_user: User, amount: int
) -> Settlement:
    if from_user.id == to_user.id:
        raise SettlementError("err_self_transfer")
    if amount <= 0:
        raise SettlementError("err_amount")

    settlement = Settlement(group_id=group.id, from_user_id=from_user.id, to_user_id=to_user.id, amount=amount)
    session.add(settlement)
    await session.flush()
    await session.refresh(settlement, ["from_user", "to_user"])
    return settlement


async def resolve_settlement(session: AsyncSession, settlement_id: int, by: User, *, confirm: bool) -> Settlement:
    """Получатель подтверждает или отклоняет перевод. Блокируем строку, чтобы двойной клик не прошёл дважды."""
    settlement = await session.scalar(
        select(Settlement).where(Settlement.id == settlement_id).with_for_update(of=Settlement)
    )
    if settlement is None:
        raise SettlementError("err_settlement_not_found")
    if settlement.to_user_id != by.id:
        raise SettlementError("err_not_recipient")
    if settlement.status != SettlementStatus.PENDING:
        raise SettlementError("err_already_resolved")

    settlement.status = SettlementStatus.CONFIRMED if confirm else SettlementStatus.REJECTED
    settlement.resolved_at = datetime.now(UTC)
    await session.flush()
    return settlement


async def has_pending_settlement(session: AsyncSession, group: Group, from_user_id: int, to_user_id: int) -> bool:
    settlement_id = await session.scalar(
        select(Settlement.id).where(
            Settlement.group_id == group.id,
            Settlement.from_user_id == from_user_id,
            Settlement.to_user_id == to_user_id,
            Settlement.status == SettlementStatus.PENDING,
        )
    )
    return settlement_id is not None
