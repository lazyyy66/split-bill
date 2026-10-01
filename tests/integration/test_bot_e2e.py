"""Сценарии «как в жизни»: несколько людей в группе пишут команды и жмут кнопки."""

import re

import pytest
from aiogram.types import Chat, ReplyKeyboardMarkup

from tests.integration.tg import Person, TgHarness, buttons, find_button

NBSP = " "


def money(text: str) -> str:
    """'по 3 000 ₸' → как бот форматирует суммы: неразрывные пробелы внутри числа и перед ₸."""
    return re.sub(r"(?<=\d) (?=\d|₸)", NBSP, text)


@pytest.fixture
async def trip(tg: TgHarness) -> tuple[Chat, Person, Person, Person]:
    """Группа, куда Роман добавил бота, а Арман и Даша нажали «Я в деле»."""
    roman = tg.person("Роман", "roman")
    arman = tg.person("Арман", "arman")
    dasha = tg.person("Даша", "dasha")
    chat = tg.group()

    [welcome] = await tg.add_bot_to_group(chat, by=roman)
    assert "Привет" in welcome.text
    for person in (arman, dasha):
        result = await person.click(welcome, "Я в деле")
        assert result.alert == "Ты в деле!"
    return chat, roman, arman, dasha


async def test_welcome_lists_everyone_who_joined(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    welcome = tg.telegram.sent[-1]  # последнее редактирование приветствия
    assert "Роман, Арман, Даша" in welcome.text
    assert (await arman.click(welcome, "Я в деле")).alert == "Ты уже в деле 👌"


async def test_full_flow_add_balance_settle_confirm(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip

    [added] = await roman.send(chat, "/add 9000 ужин в ресторане")
    assert "🍽" in added.text
    assert money("9 000 ₸") in added.text
    assert money("по 3 000 ₸") in added.text

    [balance] = await dasha.send(chat, "/balance")
    assert money("Роман: +6 000 ₸") in balance.text
    assert money("Арман: −3 000 ₸") in balance.text

    [settle] = await roman.send(chat, "/settle")
    assert "Арман → Роман" in settle.text and "Даша → Роман" in settle.text

    # Даша жмёт чужую кнопку — нельзя
    result = await dasha.click(settle, "Арман → Роман")
    assert result.alert == "Эту кнопку жмёт тот, кто переводит"
    assert result.messages == []

    # Арман отмечает перевод — Роману приходит запрос на подтверждение
    result = await arman.click(settle, "Арман → Роман")
    [request] = result.messages
    assert "Арман перевёл(а)" in request.text and money("3 000 ₸") in request.text
    assert f"tg://user?id={roman.tg.id}" in (request.html_text or request.text)  # упоминание получателя

    # повторное нажатие не создаёт дубль
    assert (await arman.click(settle, "Арман → Роман")).alert == "Этот перевод уже ждёт подтверждения"
    # подтверждать может только получатель
    assert (await arman.click(request, "Получил")).alert == "Подтвердить может только получатель"

    result = await roman.click(request, "Получил")
    [confirmed] = result.messages
    assert "получено" in confirmed.text
    assert buttons(confirmed.reply_markup) == []

    [balance] = await roman.send(chat, "/balance")
    assert money("Роман: +3 000 ₸") in balance.text
    assert money("Арман: 0 ₸") in balance.text
    assert money("Даша: −3 000 ₸") in balance.text


async def test_any_member_can_undo_expense(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    [added] = await roman.send(chat, "/add 3000 такси")

    outsider = tg.person("Чужой")
    assert (await outsider.click(added, "Отменить")).alert == "Сначала нажми «Я в деле 🙋»"

    result = await dasha.click(added, "Отменить")
    [deleted] = result.messages
    assert "<s>" in (deleted.html_text or "") or "такси" in deleted.text
    assert "Даша" in deleted.text

    [balance] = await roman.send(chat, "/balance")
    assert "в расчёте" in balance.text


async def test_partial_payment_by_reply_and_rejection(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 продукты")

    # Даша отвечает на сообщение Романа: /paid 1000 — частичный перевод
    assert roman.last_message is not None
    [request] = await dasha.send(chat, "/paid 1000", reply_to=roman.last_message)
    assert money("1 000 ₸") in request.text

    result = await roman.click(request, "Не получал")
    assert "не получил(а)" in result.messages[0].text

    [balance] = await roman.send(chat, "/balance")
    assert money("Даша: −3 000 ₸") in balance.text  # отклонённый перевод не считается

    # ответ на сообщение бота — подсказка, а не перевод боту
    [hint] = await dasha.send(chat, "/paid 1000", reply_to=request)
    assert "Формат" in hint.text


async def test_paid_with_username(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 продукты")
    [request] = await arman.send(chat, "/paid 2000 @Roman")
    await roman.click(request, "Получил")

    [balance] = await roman.send(chat, "/balance")
    assert money("Арман: −1 000 ₸") in balance.text

    [unknown] = await arman.send(chat, "/paid 2000 @nobody")
    assert "Не нашёл @nobody" in unknown.text


async def test_stale_settle_button_is_rejected(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 продукты")
    [settle] = await roman.send(chat, "/settle")

    # после /settle Арман сам оплатил крупную трату — теперь он никому не должен
    await arman.send(chat, "/add 9000 бензин")
    result = await arman.click(settle, "Арман → Роман")
    assert result.alert == "Долги уже изменились — вызови /settle заново"


async def test_add_needs_two_members(tg: TgHarness):
    roman = tg.person("Роман")
    chat = tg.group()
    await tg.add_bot_to_group(chat, by=roman)
    [reply] = await roman.send(chat, "/add 5000 пицца")
    assert "Пока в деле только ты" in reply.text


async def test_add_validates_amount(tg: TgHarness, trip):
    chat, roman, *_ = trip
    for bad in ("/add", "/add abc", "/add -5 такси", "/add 0 такси", "/add 12000р такси"):
        [reply] = await roman.send(chat, bad)
        assert "Формат" in reply.text, bad


async def test_add_understands_amount_with_spaces(tg: TgHarness, trip):
    chat, roman, *_ = trip
    [added] = await roman.send(chat, "/add 12 000 продукты")
    assert money("12 000 ₸") in added.text
    assert "<b>продукты</b>" in added.text


async def test_member_who_left_stays_in_balance(tg: TgHarness, trip):
    chat, roman, arman, dasha = trip
    await roman.send(chat, "/add 9000 продукты")
    await tg.leave_group(dasha, chat)

    [balance] = await roman.send(chat, "/balance")
    assert "Даша (вышел из чата)" in balance.text

    # в новые траты вышедшие не попадают
    [added] = await roman.send(chat, "/add 1000 вода")
    assert "Делим на 2" in added.text


# --- реквизиты ---


async def test_setpay_in_group_links_to_private_chat(tg: TgHarness, trip):
    chat, roman, *_ = trip
    [reply] = await roman.send(chat, "/setpay")
    button = find_button(reply.reply_markup, "Мой номер")
    assert button.url == "https://t.me/splitbill_test_bot?start=setpay"


async def test_setpay_from_telegram_profile(tg: TgHarness, trip):
    chat, roman, *_ = trip

    [prompt] = await roman.send(roman.private_chat, "/start setpay")
    keyboard = tg.telegram.reply_keyboard(prompt)
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    share = keyboard.keyboard[0][0]
    assert share.request_contact is True

    [saved] = await roman.share_contact("87771234567")
    assert "+7 777 123 45 67" in saved.text

    # в /settle появилась кнопка копирования номера Романа
    await roman.send(chat, "/add 9000 продукты")
    [settle] = await roman.send(chat, "/settle")
    copies = [b for b in buttons(settle.reply_markup) if "Реквизиты: Роман" in b.text]
    assert len(copies) == 2  # у каждого перевода Роману
    assert all(b.copy_text is not None and b.copy_text.text == "+7 777 123 45 67" for b in copies)
    assert not [b for b in buttons(settle.reply_markup) if b.url]  # у всех получателей есть номер — без подсказки


async def test_setpay_rejects_someone_elses_contact(tg: TgHarness, trip):
    chat, roman, arman, _ = trip
    await roman.send(roman.private_chat, "/setpay")
    [reply] = await roman.share_contact("77010000000", contact_owner=arman)
    assert "чужой контакт" in reply.text


async def test_setpay_manual_entry(tg: TgHarness, trip):
    chat, roman, *_ = trip
    await roman.send(roman.private_chat, "/setpay")
    [prompt] = await roman.send(roman.private_chat, "✏️ Ввести вручную")
    assert "Пришли номер" in prompt.text

    [saved] = await roman.send(roman.private_chat, "Kaspi Gold 4400 4301 2345 6789")
    assert "Kaspi Gold 4400 4301 2345 6789" in saved.text

    # без состояния обычный текст в личке игнорируется
    assert await roman.send(roman.private_chat, "привет") == []


async def test_setpay_cancel(tg: TgHarness, trip):
    chat, roman, *_ = trip
    await roman.send(roman.private_chat, "/setpay")
    [reply] = await roman.send(roman.private_chat, "Отмена")
    assert "ничего не меняю" in reply.text


async def test_language_switch(tg: TgHarness, trip):
    chat, roman, *_ = trip
    [reply] = await roman.send(chat, "/lang en")
    assert "English" in reply.text
    [balance] = await roman.send(chat, "/balance")
    assert "settled" in balance.text
