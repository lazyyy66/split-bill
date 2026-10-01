import json
from urllib.parse import urlencode

import pytest

from app.api.init_data import InitDataError, sign_init_data, validate_init_data

TOKEN = "123456:TEST-TOKEN"
NOW = 1_790_000_000


def make_init_data(token: str = TOKEN, auth_date: int = NOW, **extra: str) -> str:
    fields = {
        "user": json.dumps({"id": 777, "first_name": "Роман", "last_name": "К", "username": "roman"}),
        "auth_date": str(auth_date),
        "query_id": "AAH",
        **extra,
    }
    fields["hash"] = sign_init_data(fields, token)
    return urlencode(fields)


def test_valid_init_data():
    data = validate_init_data(make_init_data(start_param="g_abc"), TOKEN, now=NOW + 10)
    assert data.user.id == 777
    assert data.user.full_name == "Роман К"
    assert data.start_param == "g_abc"


def test_signed_with_other_bot_token_is_rejected():
    with pytest.raises(InitDataError, match="подпись"):
        validate_init_data(make_init_data(token="999:OTHER"), TOKEN, now=NOW)


def test_tampered_user_is_rejected():
    raw = make_init_data().replace("777", "778")
    with pytest.raises(InitDataError, match="подпись"):
        validate_init_data(raw, TOKEN, now=NOW)


def test_expired_init_data_is_rejected():
    with pytest.raises(InitDataError, match="устарела"):
        validate_init_data(make_init_data(auth_date=NOW - 2 * 24 * 3600), TOKEN, now=NOW)


@pytest.mark.parametrize("raw", ["", "user=1", "auth_date=1&hash=abc"])
def test_garbage_is_rejected(raw):
    with pytest.raises(InitDataError):
        validate_init_data(raw, TOKEN, now=NOW)


def test_missing_user_is_rejected():
    fields = {"auth_date": str(NOW)}
    fields["hash"] = sign_init_data(fields, TOKEN)
    with pytest.raises(InitDataError, match="пользователя"):
        validate_init_data(urlencode(fields), TOKEN, now=NOW)
