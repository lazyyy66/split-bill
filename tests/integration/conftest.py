"""Интеграционные тесты на настоящем Postgres из docker compose (база splitbill_test).

Схема пересоздаётся один раз за прогон. Тесты сервисов работают в транзакции, которая откатывается;
e2e-тесты бота коммитят по-настоящему, и после каждого таблицы очищаются.
Если Postgres не запущен — тесты пропускаются.
"""

import os
from collections.abc import AsyncIterator

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import User as TgUser
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from app.bot.factory import create_dispatcher
from app.db.models import Base, Category
from app.db.session import create_session_factory
from app.domain.categories import SYSTEM_CATEGORIES
from tests.integration.tg import FakeTelegram, TgHarness

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://splitbill:splitbill@localhost:5432/splitbill_test"
)


async def seed_categories(conn: AsyncConnection) -> None:
    await conn.execute(
        insert(Category), [{"code": c.code, "name": c.code, "emoji": c.emoji} for c in SYSTEM_CATEGORIES]
    )


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await seed_categories(conn)
    except OSError as error:
        pytest.skip(f"Postgres недоступен ({error}) — запусти: docker compose up -d db")
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        yield session
        await session.close()
        await transaction.rollback()


# --- e2e: настоящий Dispatcher + эмулятор Telegram ---

E2E_TABLES = "expense_history, expense_shares, expenses, settlements, group_members, users, groups"


@pytest.fixture(scope="session")
async def tg_runtime(engine: AsyncEngine) -> tuple[Dispatcher, Bot, FakeTelegram]:
    """Dispatcher и Bot создаются один раз: роутеры aiogram нельзя подключить к двум диспетчерам."""
    telegram = FakeTelegram(TgUser(id=42, is_bot=True, first_name="SplitBill", username="splitbill_test_bot"))
    bot = Bot("42:TEST", session=telegram, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(create_session_factory(engine), MemoryStorage(), webapp_short_name="app")
    return dp, bot, telegram


@pytest.fixture
async def tg(tg_runtime: tuple[Dispatcher, Bot, FakeTelegram], engine: AsyncEngine) -> AsyncIterator[TgHarness]:
    """Хендлеры коммитят по-настоящему, поэтому после теста чистим таблицы (категории оставляем)."""
    dp, bot, telegram = tg_runtime
    telegram.reset()
    yield TgHarness(dp, bot, telegram)
    async with engine.begin() as conn:
        # CASCADE заденет и categories (они ссылаются на groups) — поэтому пересоздаём системные
        await conn.execute(text(f"TRUNCATE {E2E_TABLES}, categories RESTART IDENTITY CASCADE"))
        await seed_categories(conn)
