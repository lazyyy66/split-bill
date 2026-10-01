"""Схемы запросов и ответов API. Деньги — целые числа в минимальных единицах валюты группы."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.domain.money import MAX_AMOUNT_MAJOR

# Предел для одной суммы в минимальных единицах (при exponent=2) — защита от опечаток
MaxAmount = MAX_AMOUNT_MAJOR * 100
Amount = Annotated[int, Field(gt=0, le=MaxAmount)]


# --- ответы ---


class CurrencyOut(BaseModel):
    code: str
    symbol: str
    exponent: int


class UserOut(BaseModel):
    id: int
    name: str
    username: str | None


class MeUserOut(UserOut):
    language: str
    payment_details: str | None


class MemberOut(UserOut):
    left: bool
    payment_details: str | None


class CategoryOut(BaseModel):
    id: int
    name: str
    emoji: str
    custom: bool


class GroupSummaryOut(BaseModel):
    public_id: str
    title: str
    currency: CurrencyOut
    my_balance: int


class MeOut(BaseModel):
    user: MeUserOut
    groups: list[GroupSummaryOut]


class GroupOut(BaseModel):
    public_id: str
    title: str
    currency: CurrencyOut
    is_member: bool
    me_id: int
    reminder_interval_days: int  # 0 — напоминания выключены
    members: list[MemberOut]
    categories: list[CategoryOut]


class BalanceOut(BaseModel):
    user_id: int
    amount: int


class TransferOut(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: int


class SettlementOut(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    amount: int
    status: str
    created_at: datetime


class BalancesOut(BaseModel):
    balances: list[BalanceOut]
    transfers: list[TransferOut]
    pending: list[SettlementOut]


class ShareOut(BaseModel):
    user_id: int
    amount: int


class ExpenseOut(BaseModel):
    id: int
    title: str
    amount: int
    payer_id: int
    category_id: int
    created_by: int
    created_at: datetime
    version: int
    shares: list[ShareOut]


class ExpensePageOut(BaseModel):
    items: list[ExpenseOut]
    next_before_id: int | None


class HistoryOut(BaseModel):
    action: str
    user_id: int
    created_at: datetime
    snapshot: dict[str, Any]


class ExpenseDetailOut(ExpenseOut):
    history: list[HistoryOut]


class ErrorOut(BaseModel):
    code: str
    message: str


# --- запросы ---


class EqualSplit(BaseModel):
    mode: Literal["equal"]
    user_ids: Annotated[list[int], Field(min_length=1, max_length=200)]


class ShareIn(BaseModel):
    user_id: int
    amount: Annotated[int, Field(ge=0, le=MaxAmount)]


class ExactSplit(BaseModel):
    mode: Literal["exact"]
    shares: Annotated[list[ShareIn], Field(min_length=1, max_length=200)]


Split = Annotated[EqualSplit | ExactSplit, Field(discriminator="mode")]


class ExpenseIn(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=128)]
    amount: Amount
    category_id: int
    payer_id: int
    split: Split


class ExpenseUpdateIn(ExpenseIn):
    version: int


class CategoryIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=32)]
    emoji: Annotated[str, Field(min_length=1, max_length=8)]


class SettlementIn(BaseModel):
    to_user_id: int
    amount: Amount


class GroupSettingsIn(BaseModel):
    reminder_interval_days: Literal[0, 3, 7]


class MeUpdateIn(BaseModel):
    language: Literal["ru", "en"] | None = None
    payment_details: Annotated[str | None, Field(max_length=64)] = None
