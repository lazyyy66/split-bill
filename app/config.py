from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str = "postgresql+asyncpg://splitbill:splitbill@localhost:5432/splitbill"
    redis_url: str = "redis://localhost:6379/0"
    # Короткое имя Mini App из BotFather (/newapp): ссылка t.me/<bot>/<short_name>
    webapp_short_name: str | None = None
    # Часовой пояс для напоминаний и дат в экспорте (Казахстан — UTC+5) и час напоминаний должникам
    timezone: str = "Asia/Almaty"
    reminder_hour: int = 19


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # значения берутся из окружения / .env
