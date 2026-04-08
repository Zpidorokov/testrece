# VPS без Docker + Supabase

Это самый быстрый путь, если тебе нужна просто рабочая версия для показа и продажи.

Ниже схема:

- `Ubuntu 24.04`
- `FastAPI` как systemd service
- `Next.js` как systemd service
- `nginx` как reverse proxy
- `Supabase Postgres` вместо локальной БД
- без `Redis` и без отдельного `Celery worker`

Для такого тестового production-like запуска это нормально.

## Что мы упрощаем специально

Чтобы быстро поднять рабочую версию:

- не поднимаем `Docker`
- не поднимаем локальный `Postgres`
- не поднимаем `Redis`
- не запускаем `Celery worker`
- фоновые задачи оставляем в простом режиме через `CELERY_TASK_ALWAYS_EAGER=true`

Это подходит именно для:

- демонстрации
- тестового запуска
- первых клиентов
- продажи пилота

## 1. Установить системные пакеты

```bash
sudo apt update
sudo apt install -y nginx git curl python3-venv python3-pip
```

Поставить `Node.js 20`:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

## 2. Залить проект на сервер

```bash
cd /opt
sudo mkdir -p /opt/botreceptionist
sudo chown $USER:$USER /opt/botreceptionist
git clone <YOUR_REPO_URL> /opt/botreceptionist
cd /opt/botreceptionist
```

Если репозиторий ещё не опубликован, просто передай папку на сервер через `scp` или `rsync`.

## 3. Создать Python venv и установить backend

```bash
cd /opt/botreceptionist
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

## 4. Собрать admin-web

```bash
cd /opt/botreceptionist/admin-web
npm ci
npm run build
```

## 5. Подготовить `.env`

```bash
cd /opt/botreceptionist
cp .env.example .env
nano .env
```

Для твоего случая важно заполнить так:

```dotenv
BOT_TOKEN=твой_bot_token
TELEGRAM_WEBHOOK_SECRET=длинный_случайный_секрет

OPENROUTER_API_KEY=твой_openrouter_key
OPENROUTER_MODEL=openai/gpt-4.1-mini

DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:SUPABASE_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require
REDIS_URL=redis://localhost:6379/0

DOMAIN=bot.yourdomain.com
ADMIN_WEB_URL=https://bot.yourdomain.com/admin
NEXT_PUBLIC_API_BASE_URL=https://bot.yourdomain.com

STAFF_GROUP_CHAT_ID=-100...
JWT_SECRET=очень_длинный_секрет
ALLOWED_ADMIN_IDS=123456789

ALLOW_INSECURE_TELEGRAM_INIT_DATA=false
CELERY_TASK_ALWAYS_EAGER=true
TELEGRAM_DRY_RUN=false
OPENROUTER_DRY_RUN=false

BOTRECEPTIONIST_ADMIN_TOKEN=

S3_ENDPOINT=https://your-s3-endpoint
S3_REGION=your-region
S3_BUCKET=your-bucket
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_USE_SSL=true
```

Важно:

- для `Supabase` лучше использовать `pooler` URL
- обязательно оставь `?sslmode=require`
- `REDIS_URL` пока можно оставить фиктивным, потому что в этом режиме worker не поднимается

## 6. Прогнать миграции

```bash
cd /opt/botreceptionist/backend
../.venv/bin/alembic upgrade head
```

## 7. Проверить backend вручную

```bash
cd /opt/botreceptionist/backend
PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

В другом окне:

```bash
curl http://127.0.0.1:8000/health
```

Если всё ок, останови `uvicorn` и переведи запуск в `systemd`.

## 8. Настроить systemd для backend

Открой шаблон:

- [botreceptionist-backend.service](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/systemd/botreceptionist-backend.service)

Заменить:

- `__APP_USER__` -> твой Linux пользователь
- `__APP_DIR__` -> `/opt/botreceptionist`

Потом:

```bash
sudo cp deploy/systemd/botreceptionist-backend.service /etc/systemd/system/botreceptionist-backend.service
sudo nano /etc/systemd/system/botreceptionist-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now botreceptionist-backend
sudo systemctl status botreceptionist-backend
```

Логи:

```bash
journalctl -u botreceptionist-backend -f
```

## 9. Настроить systemd для admin-web

Открой шаблон:

- [botreceptionist-admin-web.service](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/systemd/botreceptionist-admin-web.service)

Заменить:

- `__APP_USER__` -> твой Linux пользователь
- `__APP_DIR__` -> `/opt/botreceptionist`

Потом:

```bash
sudo cp deploy/systemd/botreceptionist-admin-web.service /etc/systemd/system/botreceptionist-admin-web.service
sudo nano /etc/systemd/system/botreceptionist-admin-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now botreceptionist-admin-web
sudo systemctl status botreceptionist-admin-web
```

Логи:

```bash
journalctl -u botreceptionist-admin-web -f
```

## 10. Настроить nginx

Шаблон тут:

- [nginx.nodocker.conf](/Users/dimakorolev/Documents/projects/botreceptionist/deploy/nginx.nodocker.conf)

Сделай:

```bash
sudo cp deploy/nginx.nodocker.conf /etc/nginx/sites-available/botreceptionist
sudo nano /etc/nginx/sites-available/botreceptionist
```

Замени:

- `YOUR_DOMAIN` -> твой домен

Потом включи:

```bash
sudo ln -s /etc/nginx/sites-available/botreceptionist /etc/nginx/sites-enabled/botreceptionist
sudo nginx -t
sudo systemctl reload nginx
```

## 11. Подключить HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bot.yourdomain.com
```

После этого:

- `https://bot.yourdomain.com/` -> admin-web
- `https://bot.yourdomain.com/admin` -> admin-web
- `https://bot.yourdomain.com/api/...` -> backend
- `https://bot.yourdomain.com/webhooks/telegram` -> Telegram webhook

## 12. Выставить Telegram webhook

Когда HTTPS уже работает:

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://bot.yourdomain.com/webhooks/telegram" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

Проверка:

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## 13. Первый вход в `/admin`

В `.env` уже должен быть:

```dotenv
ALLOWED_ADMIN_IDS=твой_telegram_id
```

Когда ты откроешь `/admin` через Telegram Web App, backend автоматически создаст первого `owner`.

## 14. Что нужно заполнить руками после запуска

Чтобы версия выглядела продаваемой, сразу занеси:

- услуги
- мастеров
- филиал
- базу знаний
- цены
- правила записи
- staff group с темами

## 15. Самый короткий рабочий checklist

Если совсем кратко:

```bash
sudo apt update
sudo apt install -y nginx git curl python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

git clone <repo> /opt/botreceptionist
cd /opt/botreceptionist
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd admin-web && npm ci && npm run build
cd /opt/botreceptionist
cp .env.example .env
nano .env

cd backend && ../.venv/bin/alembic upgrade head
```

Дальше:

- поднять 2 systemd service
- включить nginx
- выпустить SSL
- выставить Telegram webhook

## Что важно честно

Для тестовой продажи этот путь хороший.

Но для нормального production next step всё равно лучше такой:

- вынести `Celery` и `Redis`
- включить реальные фоновые jobs
- добавить S3 в обработку медиа
- сделать systemd `worker`
- добавить monitoring и backup policy

