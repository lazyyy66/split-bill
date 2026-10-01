import random

import pytest

from app.domain.settlement import (
    Expense,
    Payment,
    Transfer,
    minimize_transfers,
    net_balances,
    split_equal,
)

# --- split_equal ---


def test_split_equal_divisible():
    assert split_equal(900, [1, 2, 3], payer_id=1) == {1: 300, 2: 300, 3: 300}


def test_split_equal_remainder_goes_to_payer():
    assert split_equal(1000, [1, 2, 3], payer_id=2) == {1: 333, 2: 334, 3: 333}


def test_split_equal_remainder_spreads_payer_first_then_list_order():
    assert split_equal(1001, [1, 2, 3], payer_id=3) == {1: 334, 2: 333, 3: 334}


def test_split_equal_payer_not_in_shares():
    # Плательщик заплатил за других, сам не участвует — остаток первому по списку
    assert split_equal(1000, [5, 6, 7], payer_id=1) == {5: 334, 6: 333, 7: 333}


@pytest.mark.parametrize("total", [1, 2, 7, 100, 99_999, 10**12])
def test_split_equal_sum_is_exact(total):
    shares = split_equal(total, [1, 2, 3, 4, 5, 6, 7], payer_id=4)
    assert sum(shares.values()) == total
    assert max(shares.values()) - min(shares.values()) <= 1


@pytest.mark.parametrize(
    ("total", "participants"),
    [(0, [1]), (-100, [1]), (100, []), (100, [1, 1])],
)
def test_split_equal_rejects_bad_input(total, participants):
    with pytest.raises(ValueError):
        split_equal(total, participants, payer_id=1)


# --- net_balances ---


def test_net_balances_single_expense():
    expense = Expense(payer_id=1, shares=split_equal(900, [1, 2, 3], payer_id=1))
    assert net_balances([expense]) == {1: 600, 2: -300, 3: -300}


def test_net_balances_payments_reduce_debt():
    expense = Expense(payer_id=1, shares={1: 300, 2: 300, 3: 300})
    balances = net_balances([expense], [Payment(from_user=2, to_user=1, amount=300)])
    assert balances == {1: 300, 2: 0, 3: -300}


def test_net_balances_always_sum_to_zero():
    rng = random.Random(42)
    expenses = []
    for _ in range(50):
        people = rng.sample(range(1, 9), k=rng.randint(1, 8))
        payer = rng.randint(1, 8)
        expenses.append(Expense(payer, split_equal(rng.randint(1, 10**7), people, payer)))
    assert sum(net_balances(expenses).values()) == 0


# --- minimize_transfers ---


def test_no_debts_no_transfers():
    assert minimize_transfers({}) == []
    assert minimize_transfers({1: 0, 2: 0}) == []


def test_one_debtor_one_creditor():
    assert minimize_transfers({1: 500, 2: -500}) == [Transfer(2, 1, 500)]


def test_example_from_plan():
    # Роман заплатил за всех, Арман и Даша должны ему
    roman, arman, dasha = 1, 2, 3
    balances = {roman: 6800, arman: -4500, dasha: -2300}
    assert minimize_transfers(balances) == [
        Transfer(arman, roman, 4500),
        Transfer(dasha, roman, 2300),
    ]


def test_chain_is_collapsed():
    # 3 должен 2, 2 должен 1 → достаточно одного перевода 3 → 1
    expenses = [
        Expense(payer_id=1, shares={2: 1000}),
        Expense(payer_id=2, shares={3: 1000}),
    ]
    assert minimize_transfers(net_balances(expenses)) == [Transfer(3, 1, 1000)]


def test_deterministic_on_ties():
    balances = {1: 100, 2: 100, 3: -100, 4: -100}
    assert minimize_transfers(balances) == [Transfer(3, 1, 100), Transfer(4, 2, 100)]


def test_rejects_unbalanced_input():
    with pytest.raises(ValueError):
        minimize_transfers({1: 100, 2: -99})


@pytest.mark.parametrize("seed", range(200))
def test_random_balances_are_settled(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 15)
    balances = {u: rng.randint(-(10**6), 10**6) for u in range(1, n)}
    balances[n] = -sum(balances.values())

    transfers = minimize_transfers(balances)

    nonzero = sum(1 for b in balances.values() if b != 0)
    assert len(transfers) <= max(nonzero - 1, 0)
    assert all(t.amount > 0 and t.from_user != t.to_user for t in transfers)

    result = dict(balances)
    for t in transfers:
        assert balances[t.from_user] < 0 < balances[t.to_user]  # платят только должники кредиторам
        result[t.from_user] += t.amount
        result[t.to_user] -= t.amount
    assert all(b == 0 for b in result.values())
