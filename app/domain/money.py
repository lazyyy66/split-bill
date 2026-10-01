"""Парсинг и форматирование денежных сумм. Внутри всегда int в минимальных единицах."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    code: str
    symbol: str
    exponent: int  # сколько знаков после запятой: 2 → тиыны/копейки/центы


CURRENCIES: dict[str, Currency] = {
    c.code: c
    for c in [
        Currency("KZT", "₸", 2),
        Currency("RUB", "₽", 2),
        Currency("USD", "$", 2),
        Currency("EUR", "€", 2),
        Currency("UZS", "сўм", 2),
        Currency("KGS", "сом", 2),
        Currency("TRY", "₺", 2),
    ]
}
DEFAULT_CURRENCY = "KZT"

# Верхняя граница одной траты — защита от опечаток и переполнений (10 млрд в основной валюте)
MAX_AMOUNT_MAJOR = 10_000_000_000

_AMOUNT_RE = re.compile(r"^(\d+)(?:[.,](\d+))?$")
# Сумма в начале строки: «12000», «12 000», «1 500 000,50». Пробелы — только между группами по 3 цифры,
# поэтому «/add 500 2 пиццы» — это 500 и «2 пиццы».
_LEADING_AMOUNT_RE = re.compile(r"^\s*(\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)([.,]\d+)?(?=\s|$)")


class AmountError(ValueError):
    pass


def parse_amount(text: str, currency: Currency) -> int:
    """'12000' → 1200000, '99,5' → 9950 (для валюты с exponent=2)."""
    match = _AMOUNT_RE.match(text.strip())
    if not match:
        raise AmountError(f"Не похоже на сумму: {text!r}")

    major, minor = match.group(1), match.group(2) or ""
    if len(minor) > currency.exponent:
        raise AmountError(f"Слишком много знаков после запятой: {text!r}")

    amount = int(major) * 10**currency.exponent + int(minor.ljust(currency.exponent, "0") or 0)
    if amount <= 0:
        raise AmountError("Сумма должна быть больше нуля")
    if amount > MAX_AMOUNT_MAJOR * 10**currency.exponent:
        raise AmountError("Слишком большая сумма")
    return amount


def split_amount(text: str) -> tuple[str, str]:
    """'12 000 продукты' → ('12000', 'продукты'). Если сумма не найдена — ('', text)."""
    match = _LEADING_AMOUNT_RE.match(text)
    if not match:
        return "", text.strip()
    amount = re.sub(r"\s", "", match.group(1)) + (match.group(2) or "")
    return amount, text[match.end() :].strip()


def format_amount(amount: int, currency: Currency, lang: str = "ru") -> str:
    """1200000 → '12 000 ₸', 1200050 → '12 000,50 ₸' (в en — '12,000.50 ₸')."""
    sign = "−" if amount < 0 else ""
    major, minor = divmod(abs(amount), 10**currency.exponent)

    thousands_sep, decimal_sep = ("\u00a0", ",") if lang == "ru" else (",", ".")
    text = f"{major:,}".replace(",", thousands_sep)
    if minor:
        text += decimal_sep + str(minor).rjust(currency.exponent, "0")
    return f"{sign}{text}\u00a0{currency.symbol}"
