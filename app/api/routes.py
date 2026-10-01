"""Эндпоинты Mini App. Все требуют `Authorization: tma <initData>`."""

from contextlib import suppress

from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import AnyGroupDep, BotDep, GroupDep, SessionDep, UserDep
from app.api.errors import ApiError
from app.api.schemas import (
    BalanceOut,
    BalancesOut,
    CategoryIn,
    CategoryOut,
    CurrencyOut,
    ExpenseDetailOut,
    ExpenseIn,
    ExpenseOut,
    ExpensePageOut,
    ExpenseUpdateIn,
    GroupOut,
    GroupSummaryOut,
    HistoryOut,
    MemberOut,
    MeOut,
    MeUpdateIn,
    MeUserOut,
    SettlementIn,
    SettlementOut,
    ShareOut,
    TransferOut,
)
from app.bot import notify
from app.bot.texts import t
from app.db.models import Category, Expense, Group, GroupMember, Settlement, SettlementStatus, User
from app.domain.money import CURRENCIES
from app.domain.settlement import minimize_transfers, split_equal
from app.services.balances import create_settlement, group_balances, resolve_settlement
from app.services.expenses import (
    add_expense,
    create_category,
    delete_expense,
    expense_history,
    get_category,
    get_expense,
    list_categories,
    list_expenses,
    update_expense,
)
from app.services.groups import ensure_member, is_active_member, list_members, list_user_groups

router = APIRouter(prefix="/api")

IN_CHAT_STATUSES = {"creator", "administrator", "member"}


# --- сериализация ---


def currency_out(group: Group) -> CurrencyOut:
    c = CURRENCIES[group.currency]
    return CurrencyOut(code=c.code, symbol=c.symbol, exponent=c.exponent)


def category_out(category: Category, lang: str) -> CategoryOut:
    name = t(lang, f"cat_{category.code}") if category.code else category.name
    return CategoryOut(id=category.id, name=name, emoji=category.emoji, custom=category.group_id is not None)


def expense_out(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        title=expense.title,
        amount=expense.amount,
        payer_id=expense.payer_id,
        category_id=expense.category_id,
        created_by=expense.created_by,
        created_at=expense.created_at,
        version=expense.version,
        shares=[ShareOut(user_id=s.user_id, amount=s.amount) for s in expense.shares],
    )


def settlement_out(s: Settlement) -> SettlementOut:
    return SettlementOut(
        id=s.id,
        from_user_id=s.from_user_id,
        to_user_id=s.to_user_id,
        amount=s.amount,
        status=s.status,
        created_at=s.created_at,
    )


def shares_from_split(payload: ExpenseIn) -> dict[int, int]:
    split = payload.split
    if split.mode == "equal":
        if len(set(split.user_ids)) != len(split.user_ids):
            raise ApiError(400, "err_not_member")
        return split_equal(payload.amount, split.user_ids, payer_id=payload.payer_id)
    shares: dict[int, int] = {}
    for share in split.shares:
        shares[share.user_id] = shares.get(share.user_id, 0) + share.amount
    return shares


# --- пользователь ---


@router.get("/me")
async def get_me(session: SessionDep, user: UserDep) -> MeOut:
    groups = []
    for group in await list_user_groups(session, user):
        balances = await group_balances(session, group)
        groups.append(
            GroupSummaryOut(
                public_id=group.public_id,
                title=group.title,
                currency=currency_out(group),
                my_balance=balances.get(user.id, 0),
            )
        )
    return MeOut(user=me_user_out(user), groups=groups)


def me_user_out(user: User) -> MeUserOut:
    return MeUserOut(
        id=user.id,
        name=user.name,
        username=user.username,
        language=user.language,
        payment_details=user.payment_details,
    )


@router.patch("/me")
async def update_me(payload: MeUpdateIn, session: SessionDep, user: UserDep) -> MeUserOut:
    if payload.language is not None:
        user.language = payload.language
    if "payment_details" in payload.model_fields_set:
        user.payment_details = (payload.payment_details or "").strip() or None
    await session.commit()
    return me_user_out(user)


# --- группа ---


@router.get("/groups/{public_id}")
async def get_group(group: AnyGroupDep, session: SessionDep, user: UserDep) -> GroupOut:
    """Отвечает и не-участникам (is_member=false, без списка людей) — чтобы показать «Я в деле»."""
    is_member = await is_active_member(session, group, user)
    members: list[MemberOut] = []
    categories: list[CategoryOut] = []
    if is_member:
        members = [
            MemberOut(
                id=m.user.id,
                name=m.user.name,
                username=m.user.username,
                left=m.left_at is not None,
                payment_details=m.user.payment_details,
            )
            for m in await list_members(session, group, include_left=True)
        ]
        categories = [category_out(c, user.language) for c in await list_categories(session, group)]
    return GroupOut(
        public_id=group.public_id,
        title=group.title,
        currency=currency_out(group),
        is_member=is_member,
        me_id=user.id,
        members=members,
        categories=categories,
    )


@router.post("/groups/{public_id}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_group(group: AnyGroupDep, session: SessionDep, user: UserDep, bot: BotDep) -> None:
    """«Я в деле» из Mini App. Ссылку могли переслать — поэтому проверяем, что человек правда в чате."""
    member = None
    with suppress(TelegramAPIError):
        member = await bot.get_chat_member(group.tg_chat_id, user.tg_id)
    in_chat = member is not None and (
        member.status in IN_CHAT_STATUSES or (member.status == "restricted" and getattr(member, "is_member", False))
    )
    if not in_chat:
        raise ApiError(403, "err_not_in_chat")
    await ensure_member(session, group, user)
    await session.commit()


@router.get("/groups/{public_id}/balances")
async def get_balances(group: GroupDep, session: SessionDep) -> BalancesOut:
    balances = await group_balances(session, group)
    pending = await session.scalars(
        select(Settlement)
        .where(Settlement.group_id == group.id, Settlement.status == SettlementStatus.PENDING)
        .order_by(Settlement.id.desc())
    )
    return BalancesOut(
        balances=[BalanceOut(user_id=u, amount=a) for u, a in balances.items()],
        transfers=[
            TransferOut(from_user_id=tr.from_user, to_user_id=tr.to_user, amount=tr.amount)
            for tr in minimize_transfers(balances)
        ],
        pending=[settlement_out(s) for s in pending],
    )


# --- категории ---


@router.post("/groups/{public_id}/categories", status_code=status.HTTP_201_CREATED)
async def add_category(payload: CategoryIn, group: GroupDep, session: SessionDep, user: UserDep) -> CategoryOut:
    category = await create_category(session, group, payload.name, payload.emoji)
    await session.commit()
    return category_out(category, user.language)


# --- траты ---


@router.get("/groups/{public_id}/expenses")
async def get_expenses(
    group: GroupDep,
    session: SessionDep,
    before_id: int | None = None,
    limit: int = Query(30, ge=1, le=100),
) -> ExpensePageOut:
    items = await list_expenses(session, group, limit=limit + 1, before_id=before_id)
    has_more = len(items) > limit
    items = items[:limit]
    return ExpensePageOut(
        items=[expense_out(e) for e in items],
        next_before_id=items[-1].id if has_more else None,
    )


@router.post("/groups/{public_id}/expenses", status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseIn, group: GroupDep, session: SessionDep, user: UserDep, bot: BotDep
) -> ExpenseOut:
    category = await get_category(session, group, payload.category_id)
    expense = await add_expense(
        session,
        group=group,
        payer_id=payload.payer_id,
        amount=payload.amount,
        title=payload.title,
        category=category,
        shares=shares_from_split(payload),
        created_by=user,
    )
    await session.commit()
    await notify.expense_added(bot, group, expense, by=user)
    return expense_out(expense)


async def _expense_or_404(session: SessionDep, group: Group, expense_id: int) -> Expense:
    expense = await get_expense(session, group, expense_id)
    if expense is None:
        raise ApiError(404, "expense_not_found")
    return expense


@router.get("/groups/{public_id}/expenses/{expense_id}")
async def get_expense_detail(expense_id: int, group: GroupDep, session: SessionDep) -> ExpenseDetailOut:
    expense = await _expense_or_404(session, group, expense_id)
    history = [
        HistoryOut(action=h.action, user_id=h.user_id, created_at=h.created_at, snapshot=h.snapshot)
        for h in await expense_history(session, expense)
    ]
    return ExpenseDetailOut(**expense_out(expense).model_dump(), history=history)


@router.put("/groups/{public_id}/expenses/{expense_id}")
async def edit_expense(
    expense_id: int, payload: ExpenseUpdateIn, group: GroupDep, session: SessionDep, user: UserDep, bot: BotDep
) -> ExpenseOut:
    expense = await _expense_or_404(session, group, expense_id)
    category = await get_category(session, group, payload.category_id)
    await update_expense(
        session,
        expense,
        version=payload.version,
        by=user,
        payer_id=payload.payer_id,
        amount=payload.amount,
        title=payload.title,
        category=category,
        shares=shares_from_split(payload),
    )
    await session.commit()
    await notify.expense_updated(bot, group, expense, by=user)
    return expense_out(expense)


@router.delete("/groups/{public_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_expense(
    expense_id: int, version: int, group: GroupDep, session: SessionDep, user: UserDep, bot: BotDep
) -> None:
    expense = await _expense_or_404(session, group, expense_id)
    await delete_expense(session, expense, by=user, version=version)
    await session.commit()
    await notify.expense_deleted(bot, group, expense, by=user)


# --- переводы ---


@router.post("/groups/{public_id}/settlements", status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: SettlementIn, group: GroupDep, session: SessionDep, user: UserDep, bot: BotDep
) -> SettlementOut:
    """«Я перевёл» — получатель подтвердит в чате или в Mini App. Можно частично."""
    recipient = await session.get(GroupMember, (group.id, payload.to_user_id))
    if recipient is None:
        raise ApiError(400, "err_not_member")
    settlement = await create_settlement(
        session, group=group, from_user=user, to_user=recipient.user, amount=payload.amount
    )
    await notify.settlement_requested(bot, group, settlement)  # запоминает tg_message_id
    await session.commit()
    return settlement_out(settlement)


@router.post("/groups/{public_id}/settlements/{settlement_id}/{action}")
async def resolve_payment(
    settlement_id: int, action: str, group: GroupDep, session: SessionDep, user: UserDep, bot: BotDep
) -> SettlementOut:
    if action not in {"confirm", "reject"}:
        raise ApiError(404, "err_not_found")
    existing = await session.get(Settlement, settlement_id)
    if existing is None or existing.group_id != group.id:
        raise ApiError(404, "err_settlement_not_found")
    settlement = await resolve_settlement(session, settlement_id, user, confirm=action == "confirm")
    await session.commit()
    await notify.settlement_resolved(bot, group, settlement)
    return settlement_out(settlement)
