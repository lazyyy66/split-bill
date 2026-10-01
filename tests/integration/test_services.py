import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExpenseHistory, SettlementStatus, User
from app.domain.settlement import Transfer
from app.services.balances import (
    SettlementError,
    create_settlement,
    group_balances,
    has_pending_settlement,
    resolve_settlement,
    suggested_transfers,
)
from app.services.expenses import add_expense, delete_expense, get_system_category
from app.services.groups import (
    ensure_member,
    find_member_by_username,
    get_or_create_group,
    list_members,
    mark_left,
    upsert_user,
)


@pytest.fixture
async def setup(session: AsyncSession):
    group = await get_or_create_group(session, tg_chat_id=-100, title="Поездка", language="ru")
    roman = await upsert_user(session, 1, "Роман", "roman", "ru")
    arman = await upsert_user(session, 2, "Арман", "Arman_KZ", "kk")
    dasha = await upsert_user(session, 3, "Даша", None, "en")
    for user in (roman, arman, dasha):
        await ensure_member(session, group, user)
    category = await get_system_category(session, "groceries")
    return group, roman, arman, dasha, category


async def test_upsert_user_updates_name_and_keeps_language(session: AsyncSession):
    user = await upsert_user(session, 42, "Old", "old", "en")
    again = await upsert_user(session, 42, "New", "new", "ru")
    assert again.id == user.id
    assert (again.name, again.username, again.language) == ("New", "new", "en")


async def test_language_detection(setup):
    _, roman, arman, dasha, _ = setup
    assert (roman.language, arman.language, dasha.language) == ("ru", "ru", "en")


async def test_expense_split_and_balances(session: AsyncSession, setup):
    group, roman, arman, dasha, category = setup
    await add_expense(
        session,
        group=group,
        payer=roman,
        amount=100_000,
        title="продукты",
        category=category,
        participants=[roman, arman, dasha],
        created_by=roman,
    )

    balances = await group_balances(session, group)
    assert balances == {roman.id: 66_666, arman.id: -33_333, dasha.id: -33_333}
    assert await suggested_transfers(session, group) == [
        Transfer(arman.id, roman.id, 33_333),
        Transfer(dasha.id, roman.id, 33_333),
    ]


async def test_deleted_expense_is_excluded_and_logged(session: AsyncSession, setup):
    group, roman, arman, dasha, category = setup
    expense = await add_expense(
        session,
        group=group,
        payer=roman,
        amount=3000,
        title="такси",
        category=category,
        participants=[roman, arman, dasha],
        created_by=roman,
    )
    await delete_expense(session, expense, by=arman)

    assert all(b == 0 for b in (await group_balances(session, group)).values())
    actions = list(await session.scalars(select(ExpenseHistory.action).where(ExpenseHistory.expense_id == expense.id)))
    assert actions == ["create", "delete"]
    assert expense.version == 2  # оптимистичная блокировка увеличила версию


async def test_settlement_flow_with_partial_payment(session: AsyncSession, setup):
    group, roman, arman, dasha, category = setup
    await add_expense(
        session,
        group=group,
        payer=roman,
        amount=9000,
        title="ужин",
        category=category,
        participants=[roman, arman, dasha],
        created_by=roman,
    )

    settlement = await create_settlement(session, group=group, from_user=arman, to_user=roman, amount=1000)
    assert await has_pending_settlement(session, group, arman.id, roman.id)
    # пока не подтверждено — баланс не меняется
    assert (await group_balances(session, group))[arman.id] == -3000

    with pytest.raises(SettlementError, match="err_not_recipient"):
        await resolve_settlement(session, settlement.id, arman, confirm=True)

    await resolve_settlement(session, settlement.id, roman, confirm=True)
    assert settlement.status == SettlementStatus.CONFIRMED
    assert (await group_balances(session, group))[arman.id] == -2000

    with pytest.raises(SettlementError, match="err_already_resolved"):
        await resolve_settlement(session, settlement.id, roman, confirm=True)


async def test_rejected_settlement_does_not_change_balance(session: AsyncSession, setup):
    group, roman, arman, dasha, category = setup
    await add_expense(
        session,
        group=group,
        payer=roman,
        amount=9000,
        title="ужин",
        category=category,
        participants=[roman, arman, dasha],
        created_by=roman,
    )
    settlement = await create_settlement(session, group=group, from_user=dasha, to_user=roman, amount=3000)
    await resolve_settlement(session, settlement.id, roman, confirm=False)
    assert (await group_balances(session, group))[dasha.id] == -3000


async def test_self_transfer_rejected(session: AsyncSession, setup):
    group, roman, *_ = setup
    with pytest.raises(SettlementError, match="err_self_transfer"):
        await create_settlement(session, group=group, from_user=roman, to_user=roman, amount=100)


async def test_left_member_stays_in_balances(session: AsyncSession, setup):
    group, roman, arman, dasha, category = setup
    await add_expense(
        session,
        group=group,
        payer=roman,
        amount=9000,
        title="ужин",
        category=category,
        participants=[roman, arman, dasha],
        created_by=roman,
    )
    await mark_left(session, group, dasha)

    active = {m.user_id for m in await list_members(session, group)}
    everyone = {m.user_id for m in await list_members(session, group, include_left=True)}
    assert dasha.id not in active
    assert dasha.id in everyone
    assert (await group_balances(session, group))[dasha.id] == -3000

    assert await ensure_member(session, group, dasha)  # вернулась в чат
    assert dasha.id in {m.user_id for m in await list_members(session, group)}


async def test_find_member_by_username_case_insensitive(session: AsyncSession, setup):
    group, _, arman, *_ = setup
    found = await find_member_by_username(session, group, "@arman_kz")
    assert isinstance(found, User) and found.id == arman.id
    assert await find_member_by_username(session, group, "@nobody") is None
