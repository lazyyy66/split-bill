"""Проверка initData из Telegram Mini App.

Telegram подписывает данные о пользователе ключом, производным от токена бота:
    secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
    hash   = HMAC_SHA256(key=secret, msg=data_check_string)
где data_check_string — все поля, кроме hash, отсортированные по ключу, в виде "key=value" через "\\n".
Подделать подпись без токена бота нельзя — поэтому user_id берём только отсюда.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60


class InitDataError(Exception):
    pass


@dataclass(frozen=True)
class WebAppUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name


@dataclass(frozen=True)
class InitData:
    user: WebAppUser
    auth_date: int
    start_param: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Подписать поля так же, как Telegram. Нужно для тестов и локальной отладки."""
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    return hmac.new(_secret_key(bot_token), data_check_string.encode(), hashlib.sha256).hexdigest()


def validate_init_data(
    raw: str, bot_token: str, *, max_age: int = DEFAULT_MAX_AGE_SECONDS, now: float | None = None
) -> InitData:
    fields = dict(parse_qsl(raw, keep_blank_values=True, strict_parsing=False))
    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash отсутствует")

    expected_hash = sign_init_data(fields, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("неверная подпись")

    try:
        auth_date = int(fields["auth_date"])
    except KeyError, ValueError:
        raise InitDataError("нет auth_date") from None
    current = time.time() if now is None else now
    if max_age and current - auth_date > max_age:
        raise InitDataError("initData устарела")

    try:
        raw_user = json.loads(fields["user"])
        user = WebAppUser(
            id=int(raw_user["id"]),
            first_name=raw_user.get("first_name", ""),
            last_name=raw_user.get("last_name"),
            username=raw_user.get("username"),
            language_code=raw_user.get("language_code"),
        )
    except KeyError, ValueError, TypeError:
        raise InitDataError("нет данных пользователя") from None

    return InitData(user=user, auth_date=auth_date, start_param=fields.get("start_param"))
