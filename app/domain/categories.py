"""Системные категории трат и угадывание категории по названию."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemCategory:
    code: str
    emoji: str
    keywords: tuple[str, ...]  # начала слов, в нижнем регистре, ru + en


def _category(code: str, emoji: str, keywords: str) -> SystemCategory:
    return SystemCategory(code, emoji, tuple(keywords.split()))


# Порядок важен: побеждает первая категория, у которой нашлось совпадение
SYSTEM_CATEGORIES: tuple[SystemCategory, ...] = (
    _category(
        "groceries", "🛒",
        "продукт магаз супермаркет magnum small galmart вода хлеб grocer food market supermarket",
    ),
    _category(
        "cafe", "🍽",
        "кафе ресторан обед ужин завтрак кофе пицц суши бургер шаурм доставк бар пиво "
        "cafe restaurant lunch dinner breakfast coffee pizza sushi burger bar beer delivery",
    ),
    _category(
        "transport", "🚕",
        "такси яндекс бензин заправк топлив автобус метро поезд билет самолет авиа парковк "
        "taxi uber yandex fuel gas bus train ticket flight parking",
    ),
    _category(
        "housing", "🏠",
        "квартир жиль отель гостиниц хостел аренд коммунал интернет "
        "airbnb hotel hostel rent apartment booking",
    ),
    _category(
        "fun", "🎉",
        "кино концерт клуб боулинг караоке экскурс музей игр "
        "cinema movie concert club bowling karaoke tour museum game",
    ),
    _category("shopping", "🛍", "одежд подар аптек лекарств clothes gift pharmacy"),
    _category("other", "📦", ""),
)  # fmt: skip

DEFAULT_CATEGORY = "other"


def guess_category(title: str) -> str:
    """Возвращает code системной категории по словам из названия траты."""
    words = title.lower().replace("ё", "е").split()
    for category in SYSTEM_CATEGORIES:
        if any(word.startswith(keyword) for keyword in category.keywords for word in words):
            return category.code
    return DEFAULT_CATEGORY
