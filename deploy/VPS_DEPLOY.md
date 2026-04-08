# VPS deploy

Ниже самый прямой способ поднять проект на одном `VPS` через `docker compose`.

## Что получится

- `nginx` на `:80`
- `admin-web` на `Next.js`
- `backend` на `FastAPI`
- `worker` на `Celery`
- `PostgreSQL`
- `Redis`
- внешний `S3` как отдельное хранилище по env-переменным

## 1. Подготовить сервер

Минимально:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

Если `docker compose` не появился:

```bash
sudo apt install -y docker-compose-plugin
```

## 2. Залить проект на VPS

```bash
git clone <your-repo-url> botreceptionist
cd botreceptionist
```

Если репозиторий локальный и ещё не в git, сначала перенеси его на сервер любым удобным способом.

## 3. Подготовить `.env`

Скопируй шаблон:

```bash
cp .env.example .env
```

Минимально для production нужно заполнить:

```dotenv
BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openai/gpt-4.1-mini

POSTGRES_PASSWORD=сложный_пароль
DATABASE_URL=postgresql+psycopg://botreceptionist:сложный_пароль@postgres:5432/botreceptionist
REDIS_URL=redis://redis:6379/0

DOMAIN=bot.yourdomain.com
ADMIN_WEB_URL=https://bot.yourdomain.com/admin
NEXT_PUBLIC_API_BASE_URL=https://bot.yourdomain.com

STAFF_GROUP_CHAT_ID=-100...
JWT_SECRET=очень_длинный_секрет
ALLOWED_ADMIN_IDS=123456789,987654321

ALLOW_INSECURE_TELEGRAM_INIT_DATA=false
CELERY_TASK_ALWAYS_EAGER=false
TELEGRAM_DRY_RUN=false
OPENROUTER_DRY_RUN=false

S3_ENDPOINT=https://s3.your-storage.com
S3_REGION=ru-1
S3_BUCKET=botreceptionist
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_USE_SSL=true
```

Примечание:
- текущий `v1` ещё не пишет файлы в `S3`, но env уже подготовлены под следующий шаг
- если у тебя обычный AWS S3, `S3_ENDPOINT` можно не указывать или указать стандартный endpoint

## 4. Поднять стек

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f admin-web
curl http://127.0.0.1/health
```

Если всё хорошо, `backend` сам прогонит `alembic upgrade head` при старте.

## 5. Настроить домен

У домена должен быть `A record` на IP твоего VPS.

Пока SSL не настроен, можешь проверить:

- `http://your-domain/` -> admin-web
- `http://your-domain/api/...` -> backend
- `http://your-domain/webhooks/telegram` -> Telegram webhook endpoint

## 6. Настроить HTTPS

Самый простой путь — установить `certbot` на хосте и потом либо:

1. завернуть `nginx` в TLS прямо на VPS
2. или поставить внешний reverse proxy вроде `Caddy`

Если хочешь остаться на `nginx`, практичный путь такой:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Дальше временно вынеси `nginx` на хостовый конфиг или добавь отдельный SSL-конфиг и выпусти сертификат:

```bash
sudo certbot --nginx -d bot.yourdomain.com
```

Если хочешь, я отдельно подготовлю тебе сразу готовый `nginx` HTTPS-конфиг под домен.

## 7. Прописать Telegram webhook

Когда домен и HTTPS готовы, выставь webhook:

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://bot.yourdomain.com/webhooks/telegram" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

Проверить:

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## 8. Создать первого админа

В `.env` уже должен быть:

```dotenv
ALLOWED_ADMIN_IDS=123456789
```

Первый пользователь из allowlist сможет открыть `/admin` и автоматически получить роль `owner` при первом `POST /api/admin/session/init`.

## 9. Полезные команды

Пересборка после изменений:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Логи:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f nginx
```

Миграции вручную:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Shell в backend:

```bash
docker compose -f docker-compose.prod.yml exec backend sh
```

## 10. Что ещё стоит сделать после первого запуска

- заполнить `knowledge_items`
- создать `branches`, `services`, `staff_members`
- завести расписание мастеров
- добавить бота в staff group с правами на темы
- проверить `Telegram Business connection`
- включить реальный мониторинг и бэкапы Postgres

## Рекомендованная следующая доработка

Так как у тебя уже есть `S3`, следующий полезный шаг — добавить туда:

- хранение медиа-вложений из Telegram
- архив системных экспортов и логов
- резервное хранение voice/photo payload metadata

Если хочешь, я следующим сообщением могу сразу сделать второй этап:

1. добавить в код реальную интеграцию с `S3`
2. сохранить туда входящие `photo/voice/file` payload
3. обновить CRM так, чтобы staff видел ссылки на файлы

