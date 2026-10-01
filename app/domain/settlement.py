"""Расчёт долгов: делёж трат, чистые балансы, минимальный набор переводов.

Все суммы — целые числа в минимальных единицах валюты (тиын, копейка, цент).
Модуль не знает про БД и Telegram: на вход простые данные, на выход простые данные.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

UserId = int


@dataclass(frozen=True)
class Expense:
    payer_id: UserId
    shares: dict[UserId, int]  # кто сколько должен из этой траты

    @property
    def amount(self) -> int:
        return sum(self.shares.values())


@dataclass(frozen=True)
class Payment:
    """Уже совершённый перевод долга (settlement)."""

    from_user: UserId
    to_user: UserId
    amount: int


@dataclass(frozen=True)
class Transfer:
    """Перевод, который нужно сделать, чтобы обнулить балансы."""

    from_user: UserId
    to_user: UserId
    amount: int


def split_equal(total: int, participants: Sequence[UserId], payer_id: UserId) -> dict[UserId, int]:
    """Делит сумму поровну. Остаток раздаётся по одной единице: сначала плательщику
    (если он в доле), затем остальным в порядке списка.

    1000 на троих, платил второй → {1: 333, 2: 334, 3: 333}.
    """
    if total <= 0:
        raise ValueError("Сумма должна быть положительной")
    if not participants:
        raise ValueError("Нужен хотя бы один участник")
    if len(set(participants)) != len(participants):
        raise ValueError("Участники не должны повторяться")

    base, remainder = divmod(total, len(participants))
    shares = {user_id: base for user_id in participants}

    order = list(participants)
    if payer_id in shares:
        order.remove(payer_id)
        order.insert(0, payer_id)
    for user_id in order[:remainder]:
        shares[user_id] += 1

    return shares


def net_balances(expenses: Iterable[Expense], payments: Iterable[Payment] = ()) -> dict[UserId, int]:
    """Чистый баланс каждого: > 0 — ему должны, < 0 — он должен."""
    balances: dict[UserId, int] = {}

    def add(user_id: UserId, delta: int) -> None:
        balances[user_id] = balances.get(user_id, 0) + delta

    for expense in expenses:
        add(expense.payer_id, expense.amount)
        for user_id, share in expense.shares.items():
            add(user_id, -share)

    for payment in payments:
        add(payment.from_user, payment.amount)
        add(payment.to_user, -payment.amount)

    return balances


def minimize_transfers(balances: dict[UserId, int]) -> list[Transfer]:
    """Жадно сводит балансы к нулю: крупнейший должник платит крупнейшему кредитору.

    Даёт не больше n − 1 переводов (строгий минимум — NP-трудная задача).
    При равных суммах порядок определяется user_id, так что результат детерминирован.
    """
    if sum(balances.values()) != 0:
        raise ValueError("Сумма балансов должна быть равна нулю")

    debtors = sorted(((-b, u) for u, b in balances.items() if b < 0), key=lambda x: (-x[0], x[1]))
    creditors = sorted(((b, u) for u, b in balances.items() if b > 0), key=lambda x: (-x[0], x[1]))

    transfers: list[Transfer] = []
    while debtors and creditors:
        debt, debtor = debtors.pop(0)
        credit, creditor = creditors.pop(0)
        amount = min(debt, credit)
        transfers.append(Transfer(from_user=debtor, to_user=creditor, amount=amount))

        if debt > amount:
            _insert_sorted(debtors, (debt - amount, debtor))
        if credit > amount:
            _insert_sorted(creditors, (credit - amount, creditor))

    return transfers


def _insert_sorted(items: list[tuple[int, UserId]], item: tuple[int, UserId]) -> None:
    """Вставка с сохранением порядка «по убыванию суммы, затем по user_id»."""
    key = (-item[0], item[1])
    index = 0
    while index < len(items) and (-items[index][0], items[index][1]) < key:
        index += 1
    items.insert(index, item)
