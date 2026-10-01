from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str = "postgresql+asyncpg://splitbill:splitbill@localhost:5432/splitbill"
    redis_url: str = "redis://localhost:6379/0"
    # Короткое имя Mini App из BotFather (/newapp): ссылка t.me/<bot>/<short_name>
    webapp_short_name: str | None = None
    # Напоминания должникам: в какой час и по какому часовому поясу (Казахстан — UTC+5)
    reminder_hour: int = 19
    reminder_timezone: str = "Asia/Almaty"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # значения берутся из окружения / .env
