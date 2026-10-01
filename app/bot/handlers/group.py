"""Хендлеры группового чата: регистрация, траты, балансы, расчёт."""

from contextlib import suppress
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.bot import notify
from app.bot.format import expense_text, money, name, settlement_text, short_name
from app.bot.keyboards import (
    ExpenseCb,
    JoinCb,
    PayCb,
    SettlementCb,
    app_button,
    app_url,
    copy_button,
    expense_kb,
    join_kb,
    pay_button,
    setpay_link_kb,
)
from app.bot.middlewares import GROUP_CHAT_TYPES
from app.bot.texts import t
from app.db.models import Group, User
from app.domain.categories import guess_category
from app.domain.money import CURRENCIES, AmountError, parse_amount, split_amount
from app.services.balances import (
    SettlementError,
    create_settlement,
    group_balances,
    has_pending_settlement,
    resolve_settlement,
    suggested_transfers,
)
from app.services.expenses import add_equal_expense, delete_expense, get_expense, get_system_category
from app.services.groups import (
    detect_language,
    ensure_member,
    find_member_by_username,
    get_or_create_group,
    list_members,
    mark_left,
    upsert_user,
)

router = Router(name="group")
# Сообщения от анонимных админов и других ботов пропускаем — у них нет нашего User
router.message.filter(F.chat.type.in_(GROUP_CHAT_TYPES), F.from_user, ~F.from_user.is_bot)
router.callback_query.filter(F.message.chat.type.in_(GROUP_CHAT_TYPES))


# --- форматирование ---


async def mini_app_link(bot: Bot, group: Group, short_name: str | None) -> str | None:
    if not short_name:
        return None
    me = await bot.me()  # aiogram кэширует getMe
    return app_url(me.username or "", short_name, group.public_id)


async def welcome_kb(bot: Bot, group: Group, short_name: str | None) -> InlineKeyboardMarkup:
    me = await bot.me()
    return join_kb(group.language, me.username or "", await mini_app_link(bot, group, short_name))


async def welcome_text(session: AsyncSession, group: Group) -> str:
    members = await list_members(session, group)
    names = ", ".join(name(m.user) for m in members) or t(group.language, "nobody_yet")
    return t(group.language, "welcome", members=names)


async def require_group(message: Message, group: Group | None, lang: str) -> Group | None:
    if group is None:
        await message.reply(t(lang, "not_set_up"))
    return group


# --- регистрация группы и участников ---


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(
    event: ChatMemberUpdated, bot: Bot, session: AsyncSession, user: User | None, webapp_short_name: str | None
) -> None:
    if event.chat.type not in GROUP_CHAT_TYPES:
        return
    language = user.language if user else detect_language(event.from_user.language_code)
    group = await get_or_create_group(session, event.chat.id, event.chat.title or "", language)
    if user is not None:
        await ensure_member(session, group, user)

    sent = await bot.send_message(
        event.chat.id, await welcome_text(session, group), reply_markup=await welcome_kb(bot, group, webapp_short_name)
    )
    with suppress(TelegramBadRequest):  # закрепить получится, только если бота сделали админом
        await bot.pin_chat_message(event.chat.id, sent.message_id, disable_notification=True)


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
    webapp_short_name: str | None,
) -> None:
    if group is None:
        group = await get_or_create_group(session, message.chat.id, message.chat.title or "", user.language)
    await ensure_member(session, group, user)
    await message.answer(
        await welcome_text(session, group), reply_markup=await welcome_kb(bot, group, webapp_short_name)
    )


@router.callback_query(JoinCb.filter())
async def on_join(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
    webapp_short_name: str | None,
) -> None:
    if group is None:
        await callback.answer(t(lang, "not_set_up"), show_alert=True)
        return
    if not await ensure_member(session, group, user):
        await callback.answer(t(lang, "already_joined"))
        return

    await callback.answer(t(lang, "joined"))
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            await welcome_text(session, group), reply_markup=await welcome_kb(bot, group, webapp_short_name)
        )


@router.message(F.left_chat_member)
async def member_left(message: Message, session: AsyncSession, group: Group | None) -> None:
    left = message.left_chat_member
    if group is None or left is None or left.is_bot:
        return
    left_user = await upsert_user(session, left.id, left.full_name, left.username, left.language_code)
    await mark_left(session, group, left_user)


@router.message(F.migrate_to_chat_id)
async def chat_migrated(message: Message, group: Group | None) -> None:
    """Группа превратилась в супергруппу — у чата новый id, переносим кошелёк."""
    if group is not None and message.migrate_to_chat_id:
        group.tg_chat_id = message.migrate_to_chat_id


# --- траты ---


@router.message(Command("add"))
async def cmd_add(
    message: Message, command: CommandObject, session: AsyncSession, user: User, group: Group | None, lang: str
) -> None:
    if not await require_group(message, group, lang):
        return
    assert group is not None
    await ensure_member(session, group, user)

    amount_text, title = split_amount(command.args or "")
    try:
        amount = parse_amount(amount_text, CURRENCIES[group.currency])
    except AmountError:
        await message.reply(t(lang, "add_usage"))
        return
    title = title[:128] or t(lang, "default_title")

    participants = [m.user for m in await list_members(session, group)]
    if len(participants) < 2:
        await message.reply(t(lang, "add_alone"))
        return

    category = await get_system_category(session, guess_category(title))
    expense = await add_equal_expense(
        session,
        group=group,
        payer=user,
        amount=amount,
        title=title,
        category=category,
        participants=participants,
        created_by=user,
    )

    text = expense_text(group, expense)
    await message.reply(text, reply_markup=expense_kb(lang, expense.id))


@router.callback_query(ExpenseCb.filter(F.action == "del"))
async def on_delete_expense(
    callback: CallbackQuery,
    callback_data: ExpenseCb,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
) -> None:
    if group is None:
        await callback.answer(t(lang, "not_set_up"), show_alert=True)
        return
    if user.id not in {m.user_id for m in await list_members(session, group)}:
        await callback.answer(t(lang, "members_only"), show_alert=True)
        return

    expense = await get_expense(session, group, callback_data.expense_id)
    if expense is None:
        await callback.answer(t(lang, "expense_not_found"))
        return
    try:
        await delete_expense(session, expense, by=user)
    except StaleDataError:
        await callback.answer(t(lang, "err_conflict"), show_alert=True)
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            t(lang, "expense_deleted", title=escape(expense.title), amount=money(group, expense.amount), by=name(user))
        )


# --- балансы и расчёт ---


@router.message(Command("balance"))
async def cmd_balance(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
    webapp_short_name: str | None,
) -> None:
    if not await require_group(message, group, lang):
        return
    assert group is not None
    await ensure_member(session, group, user)

    balances = await group_balances(session, group)
    if not balances:
        await message.answer(t(lang, "balance_empty"))
        return
    if all(b == 0 for b in balances.values()):
        await message.answer(t(lang, "balance_settled"))
        return

    lines = [t(lang, "balance_header")]
    members = await list_members(session, group, include_left=True)
    for member in sorted(members, key=lambda m: -balances.get(m.user_id, 0)):
        balance = balances.get(member.user_id, 0)
        if member.left_at is not None and balance == 0:
            continue
        icon = "🟢" if balance > 0 else "🔴" if balance < 0 else "⚪"
        sign = "+" if balance > 0 else ""
        left = t(lang, "left_mark") if member.left_at else ""
        lines.append(f"{icon} {name(member.user)}{left}: {sign}{money(group, balance)}")
    lines += ["", t(lang, "balance_hint")]
    link = await mini_app_link(bot, group, webapp_short_name)
    markup = InlineKeyboardMarkup(inline_keyboard=[[app_button(lang, link)]]) if link else None
    await message.answer("\n".join(lines), reply_markup=markup)


@router.message(Command("settle"))
async def cmd_settle(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
    webapp_short_name: str | None,
) -> None:
    if not await require_group(message, group, lang):
        return
    assert group is not None
    await ensure_member(session, group, user)

    transfers = await suggested_transfers(session, group)
    if not transfers:
        await message.answer(t(lang, "balance_settled"))
        return

    users = {m.user_id: m.user for m in await list_members(session, group, include_left=True)}
    lines = [t(lang, "settle_header", count=len(transfers))]
    keyboard = []
    for transfer in transfers:
        debtor, creditor = users[transfer.from_user], users[transfer.to_user]
        amount = money(group, transfer.amount)
        lines.append(t(lang, "settle_line", debtor=name(debtor), creditor=name(creditor), amount=amount))

        row = [
            pay_button(
                t(lang, "btn_paid", debtor=short_name(debtor), creditor=short_name(creditor), amount=amount),
                debtor.id,
                creditor.id,
                transfer.amount,
            )
        ]
        if creditor.payment_details:
            lines.append(t(lang, "settle_pay_details", details=escape(creditor.payment_details)))
            row.append(copy_button(t(lang, "btn_copy", name=short_name(creditor)), creditor.payment_details))
        keyboard.append(row)

    if any(not users[tr.to_user].payment_details for tr in transfers):
        me = await bot.me()
        keyboard += setpay_link_kb(lang, me.username or "").inline_keyboard  # «💳 Мой номер для переводов»
    if link := await mini_app_link(bot, group, webapp_short_name):
        keyboard.append([app_button(lang, link)])
    lines += ["", t(lang, "settle_footer")]
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(PayCb.filter())
async def on_paid_button(
    callback: CallbackQuery,
    callback_data: PayCb,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
) -> None:
    if group is None or not isinstance(callback.message, Message):
        await callback.answer(t(lang, "not_set_up"), show_alert=True)
        return
    if user.id != callback_data.from_id:
        await callback.answer(t(lang, "not_your_debt"), show_alert=True)
        return

    # Кнопка могла устареть: после неё добавили траты или уже рассчитались
    balances = await group_balances(session, group)
    if (
        balances.get(callback_data.from_id, 0) > -callback_data.amount
        or balances.get(callback_data.to_id, 0) < callback_data.amount
    ):
        await callback.answer(t(lang, "settle_outdated"), show_alert=True)
        return
    if await has_pending_settlement(session, group, callback_data.from_id, callback_data.to_id):
        await callback.answer(t(lang, "settlement_already_pending"), show_alert=True)
        return

    to_user = await session.get(User, callback_data.to_id)
    assert to_user is not None
    settlement = await create_settlement(
        session, group=group, from_user=user, to_user=to_user, amount=callback_data.amount
    )
    await callback.answer()
    await notify.settlement_requested(bot, group, settlement)


@router.message(Command("paid"))
async def cmd_paid(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
) -> None:
    """/paid 3000 @username — или ответом на сообщение получателя: /paid 3000. Можно частично."""
    if not await require_group(message, group, lang):
        return
    assert group is not None
    await ensure_member(session, group, user)

    amount_text, recipient = split_amount(command.args or "")
    try:
        amount = parse_amount(amount_text, CURRENCIES[group.currency])
    except AmountError:
        await message.reply(t(lang, "paid_usage"))
        return

    to_user: User | None = None
    if recipient:
        to_user = await find_member_by_username(session, group, recipient.split()[0])
        if to_user is None:
            await message.reply(t(lang, "paid_unknown_user", username=escape(recipient.split()[0])))
            return
    elif message.reply_to_message and message.reply_to_message.from_user:
        replied = message.reply_to_message.from_user
        if not replied.is_bot:
            to_user = await upsert_user(session, replied.id, replied.full_name, replied.username, replied.language_code)
    if to_user is None:
        await message.reply(t(lang, "paid_usage"))
        return

    try:
        settlement = await create_settlement(session, group=group, from_user=user, to_user=to_user, amount=amount)
    except SettlementError as error:
        await message.reply(t(lang, error.args[0]))
        return
    await notify.settlement_requested(bot, group, settlement)


@router.callback_query(SettlementCb.filter())
async def on_settlement_resolve(
    callback: CallbackQuery,
    callback_data: SettlementCb,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
) -> None:
    if group is None:
        await callback.answer(t(lang, "not_set_up"), show_alert=True)
        return
    try:
        settlement = await resolve_settlement(session, callback_data.settlement_id, user, confirm=callback_data.confirm)
    except SettlementError as error:
        await callback.answer(t(lang, error.args[0]), show_alert=True)
        return

    text = settlement_text(group, settlement)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)


# --- экспорт ---


@router.message(Command("export"))
async def cmd_export(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    group: Group | None,
    lang: str,
    timezone: str,
) -> None:
    """Excel-таблица группы — в личку (в общий чат файл со всеми тратами не шлём)."""
    if not await require_group(message, group, lang):
        return
    assert group is not None
    await ensure_member(session, group, user)

    if await notify.send_export(bot, session, group, user, timezone=timezone):
        await message.reply(t(lang, "export_sent_group", name=name(user)))
        return
    me = await bot.me()
    open_bot = InlineKeyboardButton(text=t(lang, "btn_open_bot"), url=f"https://t.me/{me.username}?start=export")
    await message.reply(t(lang, "export_need_private"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[open_bot]]))
