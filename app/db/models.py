import secrets
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def new_public_id() -> str:
    return secrets.token_urlsafe(9)  # 12 символов, 72 бита случайности


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(128))
    username: Mapped[str | None] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(2), default="ru")
    payment_details: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created_at()


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    # Случайный id для ссылок на Mini App (t.me/<bot>/app?startapp=g_<public_id>): по нему нельзя перебрать чужие группы
    public_id: Mapped[str] = mapped_column(String(16), unique=True, default=new_public_id)
    title: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    language: Mapped[str] = mapped_column(String(2), default="ru")
    created_at: Mapped[datetime] = _created_at()
    # Напоминания должникам: раз в N дней (0 — выключены). last_reminder_at — когда отправили в последний раз
    reminder_interval_days: Mapped[int] = mapped_column(default=7, server_default="7")
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = _created_at()
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(lazy="joined")


class Category(Base):
    """group_id IS NULL — системная категория (название берётся из переводов по code)."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(8))


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(128))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _created_at()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(default=1)

    shares: Mapped[list[ExpenseShare]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", lazy="selectin"
    )
    category: Mapped[Category] = relationship(lazy="joined")
    payer: Mapped[User] = relationship(foreign_keys=[payer_id], lazy="joined")

    # Оптимистичная блокировка: UPDATE ... WHERE version = <прочитанная>
    __mapper_args__: ClassVar[dict[str, Any]] = {"version_id_col": version}


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    amount: Mapped[int] = mapped_column(BigInteger)

    expense: Mapped[Expense] = relationship(back_populates="shares")
    user: Mapped[User] = relationship(lazy="joined")


class ExpenseAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ExpenseHistory(Base):
    __tablename__ = "expense_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(16))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created_at()


class SettlementStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class Settlement(Base):
    """Перевод долга: должник отмечает «перевёл», получатель подтверждает."""

    __tablename__ = "settlements"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("from_user_id <> to_user_id", name="different_users"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default=SettlementStatus.PENDING)
    created_at: Mapped[datetime] = _created_at()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Сообщение «подтверди перевод» в группе — чтобы обновить его, если подтвердили из Mini App
    tg_message_id: Mapped[int | None] = mapped_column(BigInteger)

    from_user: Mapped[User] = relationship(foreign_keys=[from_user_id], lazy="joined")
    to_user: Mapped[User] = relationship(foreign_keys=[to_user_id], lazy="joined")
