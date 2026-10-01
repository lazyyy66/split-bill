"""FastAPI-приложение для Mini App.

Запуск: uv run uvicorn app.api.main:create_app --factory --reload --port 8000
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory


def create_app(
    settings: Settings | None = None,
    *,
    bot: Bot | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """bot и session_factory можно подменить в тестах."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        if session_factory is None:
            engine = create_engine(settings.database_url)
            app.state.session_factory = create_session_factory(engine)
        if bot is None:
            app.state.bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        yield
        if bot is None:
            await app.state.bot.session.close()
        if engine is not None:
            await engine.dispose()

    app = FastAPI(title="Split Bill API", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings = settings
    if bot is not None:
        app.state.bot = bot
    if session_factory is not None:
        app.state.session_factory = session_factory

    register_error_handlers(app)
    app.include_router(router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
