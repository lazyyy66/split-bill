"""Нормализация телефонных номеров для реквизитов."""


def format_phone(raw: str) -> str:
    """'87771234567' / '77771234567' / '+7 (777) 123-45-67' → '+7 777 123 45 67'.

    Номера Казахстана и России (+7) красиво группируем, остальные — просто '+' и цифры.
    """
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 11 and digits[0] in "78":
        d = "7" + digits[1:]
        return f"+{d[0]} {d[1:4]} {d[4:7]} {d[7:9]} {d[9:11]}"
    return f"+{digits}" if digits else raw.strip()
