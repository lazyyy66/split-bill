import re
from pathlib import Path

import pytest

from app.bot.texts import TEXTS
from app.domain.categories import SYSTEM_CATEGORIES, guess_category


@pytest.mark.parametrize(
    ("title", "code"),
    [
        ("продукты", "groceries"),
        ("Magnum на неделю", "groceries"),
        ("пицца", "cafe"),
        ("Ужин в ресторане", "cafe"),
        ("такси до аэропорта", "transport"),
        ("Бензин", "transport"),
        ("квартира на выходные", "housing"),
        ("Airbnb", "housing"),
        ("боулинг", "fun"),
        ("taxi", "transport"),
        ("dinner", "cafe"),
        ("подарок Даше", "shopping"),
        ("непонятно что", "other"),
        ("", "other"),
    ],
)
def test_guess_category(title, code):
    assert guess_category(title) == code


def test_every_category_has_translations():
    for category in SYSTEM_CATEGORIES:
        assert set(TEXTS[f"cat_{category.code}"]) == {"ru", "en"}


def test_migration_seeds_all_system_categories():
    migration = next(Path("migrations/versions").glob("*_initial.py")).read_text(encoding="utf-8")
    seeded = set(re.findall(r'\("(\w+)", "', migration))
    assert seeded == {c.code for c in SYSTEM_CATEGORIES}


def test_all_texts_have_both_languages():
    for key, variants in TEXTS.items():
        assert set(variants) == {"ru", "en"}, key
