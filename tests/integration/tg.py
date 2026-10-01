"""Эмулятор Telegram для e2e-тестов бота.

Вместо настоящего Bot API — FakeTelegram: запоминает всё, что бот отправил, и отвечает
правдоподобными объектами. TgHarness создаёт «пользователей», которые пишут команды,
жмут inline-кнопки и делятся контактом. Апдейты идут через настоящий Dispatcher,
middleware, хендлеры и Postgres — подменён только сетевой слой.
"""

import itertools
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, GetMe, SendMessage, TelegramMethod
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Contact,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
    User,
)

_ids = itertools.count(1)  # общий счётчик: уникальные id между тестами (FSM-хранилище живёт весь прогон)


def _now() -> datetime:
    return datetime.now(UTC)


class FakeTelegram(BaseSession):
    def __init__(self, bot_user: User) -> None:
        super().__init__()
        self.bot_user = bot_user
        self.chats: dict[int, Chat] = {}
        self.messages: dict[tuple[int, int], Message] = {}
        self.sent: list[Message] = []  # сообщения бота в порядке отправки (включая отредактированные)
        self.callback_answers: list[AnswerCallbackQuery] = []
        # Message.reply_markup в апдейтах бывает только inline — обычные клавиатуры храним отдельно
        self.reply_keyboards: dict[tuple[int, int], ReplyKeyboardMarkup] = {}
        self.calls: list[TelegramMethod[Any]] = []

    def reply_keyboard(self, message: Message) -> ReplyKeyboardMarkup | None:
        return self.reply_keyboards.get((message.chat.id, message.message_id))

    def reset(self) -> None:
        self.sent.clear()
        self.callback_answers.clear()
        self.calls.clear()

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109 — сигнатура задана aiogram
    ) -> Any:
        self.calls.append(method)
        match method:
            case GetMe():
                return self.bot_user
            case SendMessage():
                inline = method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
                message = Message(
                    message_id=next(_ids),
                    date=_now(),
                    chat=self.chats[int(method.chat_id)],
                    from_user=self.bot_user,
                    text=method.text,
                    reply_markup=inline,
                )
                if isinstance(method.reply_markup, ReplyKeyboardMarkup):
                    self.reply_keyboards[(message.chat.id, message.message_id)] = method.reply_markup
                self.messages[(message.chat.id, message.message_id)] = message
                self.sent.append(message)
                return message
            case EditMessageText():
                assert method.chat_id is not None and method.message_id is not None
                key = (int(method.chat_id), method.message_id)
                edited = self.messages[key].model_copy(
                    update={
                        "text": method.text,
                        "reply_markup": method.reply_markup,
                        "edit_date": int(_now().timestamp()),
                    }
                )
                self.messages[key] = edited
                self.sent.append(edited)
                return edited
            case AnswerCallbackQuery():
                self.callback_answers.append(method)
                return True
            case _:
                return True  # pin, setMyCommands и т.п.

    async def close(self) -> None:
        pass

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes]:  # pragma: no cover
        raise NotImplementedError
        yield b""


@dataclass
class Person:
    tg: User
    harness: TgHarness = field(repr=False)
    last_message: Message | None = field(default=None, repr=False)  # последнее сообщение этого человека

    @property
    def name(self) -> str:
        return self.tg.first_name

    @property
    def private_chat(self) -> Chat:
        return self.harness.register_chat(Chat(id=self.tg.id, type="private", first_name=self.tg.first_name))

    async def send(self, chat: Chat, text: str, reply_to: Message | None = None) -> list[Message]:
        """Отправить сообщение. Возвращает сообщения, которые бот отправил/отредактировал в ответ."""
        return await self.harness.feed_message(self, chat, text=text, reply_to_message=reply_to)

    async def share_contact(self, phone: str, contact_owner: Person | None = None) -> list[Message]:
        owner = contact_owner or self
        contact = Contact(phone_number=phone, first_name=owner.tg.first_name, user_id=owner.tg.id)
        return await self.harness.feed_message(self, self.private_chat, contact=contact)

    async def click(self, message: Message, button_text: str) -> ClickResult:
        """Нажать inline-кнопку, в тексте которой есть button_text."""
        return await self.harness.click(self, message, button_text)


@dataclass
class ClickResult:
    alert: str | None  # текст всплывающего ответа (answerCallbackQuery), если был
    messages: list[Message]  # что бот отправил/отредактировал в ответ


class TgHarness:
    def __init__(self, dp: Dispatcher, bot: Bot, telegram: FakeTelegram) -> None:
        self.dp = dp
        self.bot = bot
        self.telegram = telegram

    def register_chat(self, chat: Chat) -> Chat:
        self.telegram.chats.setdefault(chat.id, chat)
        return self.telegram.chats[chat.id]

    def person(self, first_name: str, username: str | None = None, language_code: str = "ru") -> Person:
        user = User(id=next(_ids), is_bot=False, first_name=first_name, username=username, language_code=language_code)
        return Person(tg=user, harness=self)

    def group(self, title: str = "Поездка в горы") -> Chat:
        return self.register_chat(Chat(id=-1_000_000_000_000 - next(_ids), type="supergroup", title=title))

    async def _feed(self, **update: Any) -> list[Message]:
        before = len(self.telegram.sent)
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), **update))
        return self.telegram.sent[before:]

    async def add_bot_to_group(self, chat: Chat, by: Person) -> list[Message]:
        event = ChatMemberUpdated(
            chat=chat,
            from_user=by.tg,
            date=_now(),
            old_chat_member=ChatMemberLeft(user=self.telegram.bot_user),
            new_chat_member=ChatMemberMember(user=self.telegram.bot_user),
        )
        return await self._feed(my_chat_member=event)

    async def feed_message(self, sender: Person, chat: Chat, **fields: Any) -> list[Message]:
        message = Message(message_id=next(_ids), date=_now(), chat=chat, from_user=sender.tg, **fields)
        sender.last_message = message
        self.telegram.messages[(chat.id, message.message_id)] = message
        return await self._feed(message=message)

    async def leave_group(self, person: Person, chat: Chat) -> list[Message]:
        return await self.feed_message(person, chat, left_chat_member=person.tg)

    async def click(self, person: Person, message: Message, button_text: str) -> ClickResult:
        current = self.telegram.messages[(message.chat.id, message.message_id)]  # с учётом редактирований
        button = find_button(current.reply_markup, button_text)
        assert button.callback_data, f"Кнопка {button.text!r} не callback-кнопка"

        answers_before = len(self.telegram.callback_answers)
        callback = CallbackQuery(
            id=str(next(_ids)),
            from_user=person.tg,
            chat_instance="test",
            message=current,
            data=button.callback_data,
        )
        messages = await self._feed(callback_query=callback)
        answers = self.telegram.callback_answers[answers_before:]
        alert = next((a.text for a in answers if a.text), None)
        return ClickResult(alert=alert, messages=messages)


def buttons(markup: Any) -> list[InlineKeyboardButton]:
    if not isinstance(markup, InlineKeyboardMarkup):
        return []
    return [button for row in markup.inline_keyboard for button in row]


def find_button(markup: Any, text: str) -> InlineKeyboardButton:
    matches = [b for b in buttons(markup) if text in b.text]
    assert len(matches) == 1, f"Ищу кнопку {text!r}, есть: {[b.text for b in buttons(markup)]}"
    return matches[0]
