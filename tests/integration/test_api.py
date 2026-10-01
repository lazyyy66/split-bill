"""API Mini App: настоящий FastAPI + Postgres + эмулятор Telegram (для уведомлений в группу)."""

import json
import time
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import httpx
import pytest
from aiogram.types import Chat
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.init_data import sign_init_data
from app.api.main import create_app
from app.config import Settings
from app.db.session import create_session_factory
from tests.integration.tg import Person, TgHarness, buttons

BOT_TOKEN = "42:TEST"  # тот же, что у бота в tg_runtime


def auth(person: Person, token: str = BOT_TOKEN) -> dict[str, str]:
    """Заголовок, который Mini App шлёт в API: initData, подписанная токеном бота."""
    fields = {
        "user": json.dumps({"id": person.tg.id, "first_name": person.tg.first_name, "username": person.tg.username}),
        "auth_date": str(int(time.time())),
    }
    fields["hash"] = sign_init_data(fields, token)
    return {"Authorization": f"tma {urlencode(fields)}"}


class Api:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get(self, person: Person, url: str, **kw) -> httpx.Response:
        return await self.client.get(url, headers=auth(person), **kw)

    async def post(self, person: Person, url: str, body: dict | None = None) -> httpx.Response:
        return await self.client.post(url, headers=auth(person), json=body)

    async def put(self, person: Person, url: str, body: dict) -> httpx.Response:
        return await self.client.put(url, headers=auth(person), json=body)

    async def patch(self, person: Person, url: str, body: dict) -> httpx.Response:
        return await self.client.patch(url, headers=auth(person), json=body)

    async def delete(self, person: Person, url: str, **kw) -> httpx.Response:
        return await self.client.delete(url, headers=auth(person), **kw)


@pytest.fixture
async def api(tg: TgHarness, engine: AsyncEngine) -> AsyncIterator[Api]:
    app = create_app(Settings(bot_token=BOT_TOKEN), bot=tg.bot, session_factory=create_session_factory(engine))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield Api(client)


@pytest.fixture
async def trip(tg: TgHarness):
    """Группа: Роман добавил бота, Арман и Даша в деле. Возвращает public_id и id людей в нашей БД."""
    roman, arman, dasha = tg.person("Роман", "roman"), tg.person("Арман", "arman"), tg.person("Даша", "dasha")
    chat = tg.group()
    [welcome] = await tg.add_bot_to_group(chat, by=roman)
    for person in (arman, dasha):
        await person.click(welcome, "Я в деле")
    return chat, roman, arman, dasha


async def group_info(api: Api, person: Person) -> tuple[str, dict[str, int], dict]:
    me = (await api.get(person, "/api/me")).json()
    public_id = me["groups"][0]["public_id"]
    group = (await api.get(person, f"/api/groups/{public_id}")).json()
    ids = {m["name"]: m["id"] for m in group["members"]}
    return public_id, ids, group


def last_group_message(tg: TgHarness, chat: Chat):
    return next(m for m in reversed(tg.telegram.sent) if m.chat.id == chat.id)


# --- авторизация ---


async def test_requires_valid_init_data(api: Api, tg: TgHarness):
    roman = tg.person("Роман")
    assert (await api.client.get("/api/me")).status_code == 401
    forged = await api.client.get("/api/me", headers=auth(roman, token="999:FORGED"))
    assert forged.status_code == 401
    assert forged.json()["code"] == "err_unauthorized"


async def test_me_without_groups(api: Api, tg: TgHarness):
    roman = tg.person("Роман", "roman")
    response = await api.get(roman, "/api/me")
    assert response.status_code == 200
    assert response.json()["user"]["name"] == "Роман"
    assert response.json()["groups"] == []


async def test_me_lists_groups_with_my_balance(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 ужин")
    me = (await api.get(arman, "/api/me")).json()
    [group] = me["groups"]
    assert group["my_balance"] == -300_000
    assert group["currency"] == {"code": "KZT", "symbol": "₸", "exponent": 2}


async def test_update_me(api: Api, tg: TgHarness):
    roman = tg.person("Роман")
    response = await api.patch(roman, "/api/me", {"payment_details": " Kaspi +7 777 ", "language": "en"})
    assert response.json()["payment_details"] == "Kaspi +7 777"
    assert response.json()["language"] == "en"


# --- членство ---


async def test_outsider_sees_only_group_title(api: Api, tg: TgHarness, trip):
    chat, roman, *_ = trip
    public_id, _, _ = await group_info(api, roman)
    stranger = tg.person("Чужой")

    group = (await api.get(stranger, f"/api/groups/{public_id}")).json()
    assert group["is_member"] is False
    assert group["members"] == [] and group["categories"] == []

    for url in ("balances", "expenses"):
        response = await api.get(stranger, f"/api/groups/{public_id}/{url}")
        assert response.status_code == 403

    assert (await api.get(stranger, "/api/groups/nonexistent")).status_code == 404


async def test_join_requires_being_in_telegram_chat(api: Api, tg: TgHarness, trip):
    chat, roman, *_ = trip
    public_id, _, _ = await group_info(api, roman)

    # ссылку переслали человеку не из чата
    stranger = tg.person("Чужой")
    response = await api.post(stranger, f"/api/groups/{public_id}/join")
    assert response.status_code == 403
    assert response.json()["code"] == "err_not_in_chat"

    # человек из чата, который ещё не нажимал «Я в деле»
    vika = tg.person("Вика")
    vika.join_chat(chat)
    assert (await api.post(vika, f"/api/groups/{public_id}/join")).status_code == 204
    assert (await api.get(vika, f"/api/groups/{public_id}")).json()["is_member"] is True


# --- траты ---


async def test_create_expense_equal_split_on_subset(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    public_id, ids, group = await group_info(api, roman)
    cafe = next(c for c in group["categories"] if c["name"] == "Кафе и рестораны")

    # Роман вносит трату, которую оплатил Арман; Даша не участвовала
    body = {
        "title": "Пицца",
        "amount": 1_000_000,
        "category_id": cafe["id"],
        "payer_id": ids["Арман"],
        "split": {"mode": "equal", "user_ids": [ids["Роман"], ids["Арман"]]},
    }
    response = await api.post(roman, f"/api/groups/{public_id}/expenses", body)
    assert response.status_code == 201, response.text
    expense = response.json()
    assert {s["user_id"]: s["amount"] for s in expense["shares"]} == {ids["Роман"]: 500_000, ids["Арман"]: 500_000}

    message = last_group_message(tg, chat)
    assert "Пицца" in message.text and "Добавил(а): Роман" in message.text
    assert [b.text for b in buttons(message.reply_markup)] == ["Отменить"]

    balances = (await api.get(dasha, f"/api/groups/{public_id}/balances")).json()
    by_user = {b["user_id"]: b["amount"] for b in balances["balances"]}
    assert by_user[ids["Арман"]] == 500_000
    assert by_user[ids["Роман"]] == -500_000
    assert balances["transfers"] == [{"from_user_id": ids["Роман"], "to_user_id": ids["Арман"], "amount": 500_000}]


async def test_create_expense_exact_split(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    public_id, ids, group = await group_info(api, roman)
    category_id = group["categories"][0]["id"]
    body = {
        "title": "Продукты",
        "amount": 900_000,
        "category_id": category_id,
        "payer_id": ids["Роман"],
        "split": {"mode": "exact", "shares": [{"user_id": ids["Арман"], "amount": 600_000}]},
    }
    bad = await api.post(roman, f"/api/groups/{public_id}/expenses", body)
    assert bad.status_code == 400
    assert bad.json() == {"code": "err_shares_sum", "message": "Сумма долей не равна сумме траты"}

    body["split"]["shares"].append({"user_id": ids["Даша"], "amount": 300_000})
    ok = await api.post(roman, f"/api/groups/{public_id}/expenses", body)
    assert ok.status_code == 201
    message = last_group_message(tg, chat)
    assert "Арман" in message.text and "Даша" in message.text  # список долей, а не «по …»


async def test_expense_validation(api: Api, tg: TgHarness, trip):
    chat, roman, *_ = trip
    public_id, ids, group = await group_info(api, roman)
    stranger_id = 10**9
    base = {"title": "x", "amount": 100, "category_id": group["categories"][0]["id"], "payer_id": ids["Роман"]}

    cases = [
        ({"split": {"mode": "equal", "user_ids": [stranger_id]}}, "err_not_member"),
        ({"payer_id": stranger_id, "split": {"mode": "equal", "user_ids": [ids["Роман"]]}}, "err_not_member"),
        ({"category_id": 10**9, "split": {"mode": "equal", "user_ids": [ids["Роман"]]}}, "err_category_not_found"),
    ]
    for override, code in cases:
        response = await api.post(roman, f"/api/groups/{public_id}/expenses", base | override)
        assert response.status_code == 400 and response.json()["code"] == code, (override, response.text)

    # схема: отрицательная сумма, пустое название
    for override in ({"amount": -5}, {"title": ""}):
        body = base | override | {"split": {"mode": "equal", "user_ids": [ids["Роман"]]}}
        assert (await api.post(roman, f"/api/groups/{public_id}/expenses", body)).status_code == 422


async def test_edit_with_optimistic_locking_and_history(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 ужин")
    public_id, ids, group = await group_info(api, roman)
    [expense] = (await api.get(roman, f"/api/groups/{public_id}/expenses")).json()["items"]

    edit = {
        "title": "Ужин + десерт",
        "amount": 1_200_000,
        "category_id": expense["category_id"],
        "payer_id": ids["Роман"],
        "split": {"mode": "equal", "user_ids": list(ids.values())},
        "version": expense["version"],
    }
    # Арман и Даша редактируют одновременно, оба видели одну и ту же версию
    first = await api.put(arman, f"/api/groups/{public_id}/expenses/{expense['id']}", edit)
    assert first.status_code == 200, first.text
    assert first.json()["version"] == expense["version"] + 1
    second = await api.put(dasha, f"/api/groups/{public_id}/expenses/{expense['id']}", edit | {"title": "Другое"})
    assert second.status_code == 409
    assert second.json()["code"] == "err_conflict"

    detail = (await api.get(roman, f"/api/groups/{public_id}/expenses/{expense['id']}")).json()
    assert detail["title"] == "Ужин + десерт"
    assert [h["action"] for h in detail["history"]] == ["create", "update"]
    assert detail["history"][0]["snapshot"]["amount"] == 900_000
    assert "Арман изменил(а) трату" in last_group_message(tg, chat).text


async def test_edit_can_drop_and_add_participants(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 ужин")
    public_id, ids, _ = await group_info(api, roman)
    [expense] = (await api.get(roman, f"/api/groups/{public_id}/expenses")).json()["items"]

    edit = {
        "title": "ужин",
        "amount": 900_000,
        "category_id": expense["category_id"],
        "payer_id": ids["Роман"],
        "split": {
            "mode": "exact",
            "shares": [{"user_id": ids["Роман"], "amount": 0}, {"user_id": ids["Даша"], "amount": 900_000}],
        },
        "version": expense["version"],
    }
    updated = (await api.put(roman, f"/api/groups/{public_id}/expenses/{expense['id']}", edit)).json()
    assert {s["user_id"]: s["amount"] for s in updated["shares"]} == {ids["Даша"]: 900_000}


async def test_delete_expense(api: Api, tg: TgHarness, trip):
    chat, roman, arman, _ = trip
    await roman.send(chat, "/add 9000 ужин")
    public_id, _, _ = await group_info(api, roman)
    [expense] = (await api.get(roman, f"/api/groups/{public_id}/expenses")).json()["items"]
    url = f"/api/groups/{public_id}/expenses/{expense['id']}"

    assert (await api.delete(arman, url, params={"version": expense["version"] + 5})).status_code == 409
    assert (await api.delete(arman, url, params={"version": expense["version"]})).status_code == 204
    assert (await api.get(roman, f"/api/groups/{public_id}/expenses")).json()["items"] == []
    assert (await api.get(roman, url)).status_code == 404
    assert "Отменил(а): Арман" in last_group_message(tg, chat).text


async def test_expenses_pagination(api: Api, tg: TgHarness, trip):
    chat, roman, *_ = trip
    for amount in range(1, 6):
        await roman.send(chat, f"/add {amount}00 вода")
    public_id, _, _ = await group_info(api, roman)

    page1 = (await api.get(roman, f"/api/groups/{public_id}/expenses", params={"limit": 2})).json()
    assert [e["amount"] for e in page1["items"]] == [50_000, 40_000]
    page2 = (
        await api.get(
            roman, f"/api/groups/{public_id}/expenses", params={"limit": 2, "before_id": page1["next_before_id"]}
        )
    ).json()
    assert [e["amount"] for e in page2["items"]] == [30_000, 20_000]
    page3 = (
        await api.get(
            roman, f"/api/groups/{public_id}/expenses", params={"limit": 2, "before_id": page2["next_before_id"]}
        )
    ).json()
    assert [e["amount"] for e in page3["items"]] == [10_000]
    assert page3["next_before_id"] is None


# --- категории ---


async def test_custom_categories(api: Api, tg: TgHarness, trip):
    chat, roman, arman, _ = trip
    public_id, ids, _ = await group_info(api, roman)

    created = await api.post(roman, f"/api/groups/{public_id}/categories", {"name": "Боулинг", "emoji": "🎳"})
    assert created.status_code == 201
    assert created.json()["custom"] is True
    duplicate = await api.post(arman, f"/api/groups/{public_id}/categories", {"name": "боулинг", "emoji": "🎳"})
    assert duplicate.json()["code"] == "err_category_exists"

    categories = (await api.get(arman, f"/api/groups/{public_id}")).json()["categories"]
    assert categories[-1]["name"] == "Боулинг"
    assert categories[0] == {"id": categories[0]["id"], "name": "Продукты", "emoji": "🛒", "custom": False}

    # своя категория другой группы недоступна
    other_chat = tg.group("Другая")
    vika = tg.person("Вика")
    [welcome] = await tg.add_bot_to_group(other_chat, by=vika)
    await roman.click(welcome, "Я в деле")
    other_id = next(g for g in (await api.get(vika, "/api/me")).json()["groups"])["public_id"]
    vika_ids = {m["name"]: m["id"] for m in (await api.get(vika, f"/api/groups/{other_id}")).json()["members"]}
    body = {
        "title": "x",
        "amount": 100,
        "category_id": created.json()["id"],
        "payer_id": vika_ids["Вика"],
        "split": {"mode": "equal", "user_ids": [vika_ids["Вика"], vika_ids["Роман"]]},
    }
    response = await api.post(vika, f"/api/groups/{other_id}/expenses", body)
    assert response.json()["code"] == "err_category_not_found"


# --- переводы ---


async def test_settlement_from_app_confirmed_in_app_updates_chat(api: Api, tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 ужин")
    public_id, ids, _ = await group_info(api, roman)

    created = await api.post(
        arman, f"/api/groups/{public_id}/settlements", {"to_user_id": ids["Роман"], "amount": 100_000}
    )
    assert created.status_code == 201
    settlement = created.json()
    request = last_group_message(tg, chat)
    assert "Арман перевёл(а)" in request.text
    assert len(buttons(request.reply_markup)) == 2

    pending = (await api.get(roman, f"/api/groups/{public_id}/balances")).json()["pending"]
    assert [p["id"] for p in pending] == [settlement["id"]]

    url = f"/api/groups/{public_id}/settlements/{settlement['id']}"
    assert (await api.post(arman, f"{url}/confirm")).json()["code"] == "err_not_recipient"
    confirmed = await api.post(roman, f"{url}/confirm")
    assert confirmed.json()["status"] == "confirmed"

    # сообщение в чате обновилось и потеряло кнопки
    edited = tg.telegram.messages[(chat.id, request.message_id)]
    assert "получено" in edited.text
    assert buttons(edited.reply_markup) == []

    balances = (await api.get(roman, f"/api/groups/{public_id}/balances")).json()
    by_user = {b["user_id"]: b["amount"] for b in balances["balances"]}
    assert by_user[ids["Арман"]] == -200_000
    assert balances["pending"] == []


async def test_settlement_from_app_confirmed_in_chat(api: Api, tg: TgHarness, trip):
    chat, roman, arman, _ = trip
    await roman.send(chat, "/add 9000 ужин")
    public_id, ids, _ = await group_info(api, roman)
    await api.post(arman, f"/api/groups/{public_id}/settlements", {"to_user_id": ids["Роман"], "amount": 300_000})

    result = await roman.click(last_group_message(tg, chat), "Получил")
    assert "получено" in result.messages[0].text
    balances = (await api.get(roman, f"/api/groups/{public_id}/balances")).json()
    assert balances["transfers"] == [{"from_user_id": ids["Даша"], "to_user_id": ids["Роман"], "amount": 300_000}]


async def test_settlement_to_stranger_rejected(api: Api, tg: TgHarness, trip):
    chat, roman, arman, _ = trip
    public_id, ids, _ = await group_info(api, roman)
    response = await api.post(arman, f"/api/groups/{public_id}/settlements", {"to_user_id": 10**9, "amount": 100})
    assert response.json()["code"] == "err_not_member"
    response = await api.post(
        arman, f"/api/groups/{public_id}/settlements", {"to_user_id": ids["Арман"], "amount": 100}
    )
    assert response.json()["code"] == "err_self_transfer"
