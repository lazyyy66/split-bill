import pytest

from app.domain.money import CURRENCIES, AmountError, format_amount, parse_amount

KZT = CURRENCIES["KZT"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12000", 1_200_000),
        ("1", 100),
        ("99.5", 9_950),
        ("99,5", 9_950),
        ("99,05", 9_905),
        ("0.01", 1),
        (" 500 ", 50_000),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text, KZT) == expected


@pytest.mark.parametrize("text", ["", "abc", "12 000", "-5", "0", "0.00", "1.001", "1e5", "12000р", "1,2,3"])
def test_parse_amount_rejects(text):
    with pytest.raises(AmountError):
        parse_amount(text, KZT)


def test_parse_amount_rejects_huge():
    with pytest.raises(AmountError):
        parse_amount("100000000000", KZT)


@pytest.mark.parametrize(
    ("amount", "lang", "expected"),
    [
        (1_200_000, "ru", "12 000 ₸"),
        (1_200_050, "ru", "12 000,50 ₸"),
        (1_200_050, "en", "12,000.50 ₸"),
        (5, "ru", "0,05 ₸"),
        (-450_000, "ru", "−4 500 ₸"),
        (0, "ru", "0 ₸"),
    ],
)
def test_format_amount(amount, lang, expected):
    assert format_amount(amount, KZT, lang) == expected
