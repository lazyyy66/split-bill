# Split Bill — «Кто кому должен»

Telegram-бот + Mini App для учёта общих расходов в группах (Splitwise внутри Telegram).
Полный план, модель данных и задачи по этапам — в [PLAN.md](PLAN.md).

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
- Новые фичи бота покрываем e2e-сценарием в `tests/integration/test_bot_e2e.py` (эмулятор Telegram — `tests/integration/tg.py`: пользователи пишут команды, жмут кнопки, шлют контакт).

## Git
- Работа делится на **этапы**, не недели: коммиты называем `Этап N: …` (этапы — таблица в PLAN.md).
- Репозиторий: https://github.com/lazyyy66/split-bill, ветка `main`.

## Нюансы Telegram
- В группах кнопка `web_app` не работает → используем direct link `t.me/<bot>/<app>?startapp=g_<group_id>`.
- Privacy mode: в группе бот видит только команды — для MVP достаточно.
- Бот не знает участников группы заранее → регистрация через кнопку «Я в деле 🙋» или при первом открытии Mini App.

## Команды
```
docker compose up -d db redis        # Postgres + Redis (база splitbill и splitbill_test)
uv run alembic upgrade head          # применить миграции
uv run python -m app.bot             # бот в режиме polling
uv run uvicorn app.api.main:create_app --factory --reload --port 8000   # API для Mini App (/api/docs)
cd webapp && npm run dev             # Mini App (Vite, :5173, /api проксируется на :8000)
ngrok http 5173 --url=<статичный-домен>   # HTTPS для Mini App при локальной разработке
cd webapp && npm run typecheck       # проверка типов фронта
uv run pytest                        # тесты (интеграционные — на splitbill_test)
uv run ruff check . && uv run ruff format .
uv run alembic revision --autogenerate -m "..."   # новая миграция после изменения моделей
docker compose --profile full up -d  # всё в контейнерах, включая бота
```

## Структура
- `app/domain/` — чистая логика без БД и Telegram: деньги, делёж, минимальные переводы, категории.
- `app/services/` — работа с БД (AsyncSession); переиспользуется ботом и будущим API.
- `app/bot/` — aiogram: `factory.py` (сборка Dispatcher — общая для запуска и тестов), `handlers/`, `keyboards.py`, `texts.py` (ru/en), `middlewares.py` (сессия БД + user/group/lang). FSM-состояния — в Redis.
- `app/api/` — FastAPI для Mini App: `init_data.py` (проверка подписи), `deps.py` (текущий пользователь, группа с проверкой членства), `routes.py`, `schemas.py`, `errors.py`.
- `app/bot/format.py` + `notify.py` — тексты сообщений и уведомления в группу; общие для хендлеров бота и API.
- `webapp/` — Mini App: React + TypeScript + Vite, без UI-библиотек; цвета из темы Telegram (`--tg-theme-*`), нативные MainButton/BackButton. Деньги на фронте — тоже целые минимальные единицы (`src/money.ts` повторяет логику бэкенда).
- Ошибки сервисов — исключения с ключом текста (`err_*`), бот переводит их через `t(lang, key)`, API отдаёт `{code, message}`.

## Текущий статус
Бот: @splitbill66bot. Этап 1 готов (бот). Этап 2: API + Mini App написаны и покрыты тестами (API — интеграционными); вживую в Telegram Mini App ещё не проверялась. Нужно: ngrok-домен → BotFather /newapp → `WEBAPP_SHORT_NAME` в `.env`.
