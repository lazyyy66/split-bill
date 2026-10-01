"""Интеграционные тесты на настоящем Postgres из docker compose (база splitbill_test).

Схема пересоздаётся один раз за прогон, каждый тест работает в транзакции, которая откатывается.
Если Postgres не запущен — тесты пропускаются.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.db.models import Base, Category
from app.domain.categories import SYSTEM_CATEGORIES

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://splitbill:splitbill@localhost:5432/splitbill_test"
)


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                insert(Category), [{"code": c.code, "name": c.code, "emoji": c.emoji} for c in SYSTEM_CATEGORIES]
            )
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
