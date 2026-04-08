# BotReceptionist

Telegram Business AI-бот для салона красоты с:

- backend на `FastAPI + SQLAlchemy + Celery`
- `PostgreSQL`-совместимой схемой и `Alembic`
- AI routing через `OpenRouter` adapter со structured output fallback
- внутренним `Next.js` Web App для staff
- staff group topics, takeover, booking engine и audit trail

## Структура

- [backend](/Users/dimakorolev/Documents/projects/botreceptionist/backend) — FastAPI API, Telegram webhook, CRM, booking engine, AI router, Celery tasks
- [admin-web](/Users/dimakorolev/Documents/projects/botreceptionist/admin-web) — Next.js App Router Web App для `/admin`
- [zadanie](/Users/dimakorolev/Documents/projects/botreceptionist/zadanie) — исходные ТЗ

## Backend

### Что уже реализовано

- `POST /webhooks/telegram` с проверкой `X-Telegram-Bot-Api-Secret-Token`
- business update flow: создание `client`, `dialog`, `lead`, `forum topic`, логирование сообщений, AI reply, notifications
- `POST /api/admin/session/init` и `GET /api/admin/me`
- CRM API: `clients`, `dialogs`, `bookings`, `schedule`, `knowledge`, `analytics`, `notifications`, `audit logs`
- manual takeover и возврат в auto
- внутренний booking engine `v1` на одну услугу
- Celery task definitions для staff alerts, reminders и AI jobs
- pytest-сценарии на auth, webhook flow и booking conflict

### Быстрый запуск

1. Скопируйте `.env.example` в `.env`.
2. Активируйте окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

3. Для локального dry-run достаточно дефолтных флагов:
   `TELEGRAM_DRY_RUN=true`, `OPENROUTER_DRY_RUN=true`, `ALLOW_INSECURE_TELEGRAM_INIT_DATA=true`
4. Запустите API:

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

5. При необходимости прогоните миграции:

```bash
cd backend
../.venv/bin/alembic upgrade head
```

6. Для Celery worker:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## Admin Web App

### Что уже реализовано

- `Dashboard`
- `Dialogs` с manual actions через Next.js proxy routes
- `Clients`
- `Client Card`
- `Bookings`
- `Knowledge`
- `Settings`

### Запуск

```bash
cd admin-web
npm install
npm run dev
```

Для server-side чтения и proxy-записей полезно указать:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
BOTRECEPTIONIST_ADMIN_TOKEN=<jwt от /api/admin/session/init>
```

Если токен не задан, страницы откроются с fallback-данными, а mutating actions будут возвращать понятную ошибку.

## Тесты

```bash
.venv/bin/pytest backend/tests
```

## VPS deploy

Для production-развёртывания на своём сервере я добавил:

- [docker-compose.prod.yml](/Users/dimakorolev/Documents/projects/botreceptionist/docker-compose.prod.yml)
- [backend/Dockerfile](/Users/dimakorolev/Documents/projects/botreceptionist/backend/Dockerfile)
- [admin-web/Dockerfile](/Users/dimakorolev/Documents/projects/botreceptionist/admin-web/Dockerfile)
- [deploy/nginx.conf](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/nginx.conf)
- [deploy/VPS_DEPLOY.md](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/VPS_DEPLOY.md)

Быстрый старт на VPS:

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
```

Подробно:
- [VPS_DEPLOY.md](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/VPS_DEPLOY.md)

## VPS без Docker

Если тебе нужен быстрый тестовый запуск на `Ubuntu 24.04` без Docker и с `Supabase`, я добавил отдельный путь:

- [VPS_NODOCKER_SUPABASE.md](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/VPS_NODOCKER_SUPABASE.md)
- [botreceptionist-backend.service](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/systemd/botreceptionist-backend.service)
- [botreceptionist-admin-web.service](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/systemd/botreceptionist-admin-web.service)
- [nginx.nodocker.conf](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/nginx.nodocker.conf)

## Production notes

- Telegram Business ответы уходят через `business_connection_id`
- темы staff group создаются через `createForumTopic` и используются только как observer/sync контур
- `/admin` остаётся закрытым серверной авторизацией по Telegram user ID и роли
- voice flow в `v1` поддерживает транскрипт из payload; если транскрипта нет, система создаёт alert staff
- по умолчанию `create_all()` выполняется на startup для dev bootstrap; для production опирайтесь на Alembic
