import pytest

from app.domain.phone import format_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("77771234567", "+7 777 123 45 67"),
        ("+77771234567", "+7 777 123 45 67"),
        ("87771234567", "+7 777 123 45 67"),
        ("+7 (777) 123-45-67", "+7 777 123 45 67"),
        ("998901234567", "+998901234567"),
        ("+49 151 23456789", "+4915123456789"),
    ],
)
def test_format_phone(raw, expected):
    assert format_phone(raw) == expected
