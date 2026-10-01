# Split Bill — «Кто кому должен»

Telegram-бот + Mini App для учёта общих расходов в группах (Splitwise внутри Telegram).
Полный план, модель данных и задачи по неделям — в [PLAN.md](PLAN.md).

## Про автора
- Роман, пишет на Python, бэкенд. Учится в IT STEP (Django). Уже делал бота на aiogram 3 (`../Video Downloader Bot`).
- Общаемся на русском.
- Цель проекта: публичный продукт с реальными пользователями (компании друзей, поездки), а не локальная утилита. Одновременно — сильный проект для портфолио.

## Стек
- Python 3.14, FastAPI (API для Mini App + webhook бота), aiogram 3
- PostgreSQL + SQLAlchemy 2 (async) + Alembic
- Redis + arq — фоновые задачи (распознавание чеков, напоминания)
- Mini App: Vite + React (или Vue) + `telegram-web-app.js`; фронт минимальный, 4–5 экранов
- Docker Compose; прод — VPS + Caddy (HTTPS обязателен для Mini App); локально — туннель cloudflared

## Правила для кода
- **Деньги — только целые числа в минимальных единицах (тиын/копейка) или Decimal. Никогда float.**
- `user_id` в API берём только из проверенного `initData` (HMAC с токеном бота), никогда из тела запроса.
- Секреты (токен бота, ключи LLM) — только в `.env`, который в `.gitignore`. Токены в чат не вставлять.
- Алгоритм расчёта долгов покрыт unit-тестами (pytest).

## Нюансы Telegram
- В группах кнопка `web_app` не работает → используем direct link `t.me/<bot>/<app>?startapp=g_<group_id>`.
- Privacy mode: в группе бот видит только команды — для MVP достаточно.
- Бот не знает участников группы заранее → регистрация через кнопку «Я в деле 🙋» или при первом открытии Mini App.

## Команды
```
docker compose up -d db redis        # Postgres + Redis (база splitbill и splitbill_test)
uv run alembic upgrade head          # применить миграции
uv run python -m app.bot             # бот в режиме polling
uv run pytest                        # тесты (интеграционные — на splitbill_test)
uv run ruff check . && uv run ruff format .
uv run alembic revision --autogenerate -m "..."   # новая миграция после изменения моделей
docker compose --profile full up -d  # всё в контейнерах, включая бота
```

## Структура
- `app/domain/` — чистая логика без БД и Telegram: деньги, делёж, минимальные переводы, категории.
- `app/services/` — работа с БД (AsyncSession); переиспользуется ботом и будущим API.
- `app/bot/` — aiogram: `handlers/`, `keyboards.py`, `texts.py` (ru/en), `middlewares.py` (сессия БД + user/group/lang).
- Ошибки сервисов — исключения с ключом текста (`err_*`), бот переводит их через `t(lang, key)`.

## Текущий статус
Бот: @splitbill66bot. Неделя 1 готова: Docker Compose, модели + миграции, бот (`/add`, `/balance`, `/settle`, `/paid`, `/setpay`, `/lang`), тесты. Дальше — неделя 2: FastAPI + проверка initData, Mini App. Своих категорий группы пока можно добавить только в БД — UI для них будет в Mini App.
