Ниже — вторая часть: уже не общее ТЗ, а техническая спецификация под разработку. Я буду исходить из архитектуры на Telegram Business + connected business bot, где бот может отвечать от имени бизнес-аккаунта, а внутренняя часть открывается через /admin и Telegram Web App. Telegram это официально поддерживает, вместе с business connection, business messages, command scopes для наборов команд и forum topics / message_thread_id для работы с темами.  ￼

Техническая спецификация

Проект: Telegram AI-бот салона красоты

Часть 2. API, user flows, состояния, экраны, интеграционная логика

1. Границы системы

Система состоит из 5 подсистем:
    1.    Telegram Business integration
    2.    Backend API
    3.    AI orchestration layer
    4.    Admin Web App
    5.    PostgreSQL + очередь + хранилище

1.1. Внешние интерфейсы

Внешние точки интеграции:
    •    Telegram Bot API / business updates
    •    AI provider API
    •    PostgreSQL
    •    Redis / очередь
    •    файловое хранилище
    •    опционально внешний календарь / CRM

⸻

2. High-level архитектура

2.1. Поток клиентского сообщения
    1.    Клиент пишет на Telegram-аккаунт салона
    2.    Telegram передаёт update подключённому business bot
    3.    Webhook endpoint принимает update
    4.    Backend валидирует и дедуплицирует update
    5.    Система ищет/создаёт клиента и диалог
    6.    Система логирует сообщение
    7.    Система решает:
    •    auto reply
    •    manual only
    •    escalation
    8.    AI получает контекст + знания + данные о слотах
    9.    Backend отправляет ответ через Telegram от имени business account
    10.    Сообщение дублируется в staff group topic
    11.    Обновляются статусы, уведомления и аналитика

2.2. Поток сотрудника через /admin
    1.    Сотрудник пишет /admin
    2.    Бот проверяет user ID и роль
    3.    Бот отдаёт кнопку открытия Web App
    4.    Web App проходит серверную auth-сессию
    5.    Пользователь работает в CRM-интерфейсе

Telegram command scopes подходят для управления видимостью команд, но этого недостаточно для авторизации — серверная проверка роли обязательна.  ￼

⸻

3. Backend-модули

Ниже — рекомендуемая модульная разбивка.

3.1. telegram-webhook

Отвечает за:
    •    приём update
    •    signature / secret token validation
    •    дедупликацию
    •    маршрутизацию событий

3.2. business-message-processor

Отвечает за:
    •    разбор business_message
    •    разбор edited_business_message
    •    связь с business_connection_id
    •    отправку ответов от имени business account

Bot API поддерживает business_connection_id при отправке сообщений и business-related updates для работы от имени подключённого аккаунта.  ￼

3.3. crm-core

Отвечает за:
    •    clients
    •    dialogs
    •    leads
    •    bookings
    •    statuses
    •    notes
    •    staff assignments

3.4. scheduling-engine

Отвечает за:
    •    календарь мастеров
    •    слоты
    •    буферы
    •    пересечения
    •    переносы
    •    отмены

3.5. ai-router

Отвечает за:
    •    intent detection
    •    risk detection
    •    retrieval по базе знаний
    •    prompt assembly
    •    response post-check
    •    escalation rules

3.6. topic-sync

Отвечает за:
    •    создание темы в staff group
    •    дублирование сообщений
    •    системные события по клиенту
    •    ссылки между client/dialog и topic

3.7. admin-api

Отвечает за:
    •    Web App endpoints
    •    роли
    •    фильтры
    •    CRUD по сущностям
    •    analytics

3.8. notification-service

Отвечает за:
    •    staff alerts
    •    reminders
    •    follow-up задачи
    •    failed message alerts

3.9. audit-log

Отвечает за:
    •    запись действий системы
    •    запись действий сотрудника
    •    AI decision trace

⸻

4. Состояния сущностей

4.1. Состояния диалога dialog.status
    •    new
    •    active
    •    waiting_client
    •    waiting_slot_selection
    •    booked
    •    escalated
    •    manual
    •    closed
    •    lost

4.2. Режим диалога dialog.mode
    •    auto
    •    manual
    •    hybrid

Правила:
    •    auto — AI отвечает сам
    •    manual — AI не отвечает вообще
    •    hybrid — AI предлагает черновик, сотрудник подтверждает

4.3. Состояния лида lead.stage
    •    new
    •    qualified
    •    service_selected
    •    slot_selected
    •    booked
    •    canceled
    •    lost
    •    returning

4.4. Состояния записи booking.status
    •    pending
    •    confirmed
    •    rescheduled
    •    canceled_by_client
    •    canceled_by_staff
    •    completed
    •    no_show

4.5. Состояния клиента client.status
    •    new
    •    consulting
    •    interested
    •    booking_in_progress
    •    booked
    •    loyal
    •    vip
    •    problematic
    •    archived

⸻

5. User flows

5.1. Flow A — новый клиент, консультация, запись

Шаги
    1.    Клиент пишет вопрос
    2.    Backend создаёт client, dialog, lead
    3.    Создаётся topic в staff group
    4.    AI определяет intent = consultation / booking
    5.    AI отвечает и подталкивает к уточнению:
    •    услуга
    •    мастер
    •    дата
    6.    Scheduling engine подбирает слоты
    7.    Клиент выбирает слот
    8.    Создаётся booking
    9.    Клиент получает подтверждение
    10.    Staff получает уведомление
    11.    Dialog и lead переводятся в booked

5.2. Flow B — перенос записи
    1.    Клиент пишет “хочу перенести”
    2.    Система ищет active booking
    3.    AI показывает доступные новые интервалы
    4.    Клиент выбирает
    5.    Запись обновляется
    6.    Staff получает уведомление
    7.    В topic пишется событие “перенос”

5.3. Flow C — отмена
    1.    Клиент инициирует отмену
    2.    AI подтверждает действие
    3.    Booking получает статус canceled
    4.    Клиенту отправляется подтверждение
    5.    Lead переводится в returning или lost
    6.    Система может предложить новую дату

5.4. Flow D — неудобный вопрос / жалоба
    1.    AI определяет risk = high
    2.    Диалог переводится в escalated
    3.    Staff получает urgent alert
    4.    Topic помечается как конфликтный
    5.    AI больше не отвечает, пока диалог не вернут в auto/manual policy

5.5. Flow E — сотрудник берёт диалог
    1.    В карточке клиента нажимается “Take over”
    2.    dialog.mode = manual
    3.    dialog.assigned_user_id = staff_id
    4.    Клиентские сообщения продолжают логироваться
    5.    Автоответы отключены

⸻

6. Telegram-specific логика

6.1. Business routing

Для каждого входящего диалога должны храниться:
    •    business_connection_id
    •    telegram_chat_id
    •    client_telegram_user_id

Это нужно, чтобы отвечать именно в правильный бизнес-чат от имени нужного аккаунта. Bot API использует business_connection_id при отправке сообщений от лица business account.  ￼

6.2. Topic routing

Для staff group должны храниться:
    •    staff_group_chat_id
    •    forum_topic_id
    •    message_thread_id

Telegram поддерживает message_thread_id для отправки сообщений в конкретную тему форума.  ￼

6.3. Admin command visibility

Нужно настроить отдельный набор bot commands для сотрудников через scope, но реальная авторизация должна идти через backend allowlist / roles.  ￼

⸻

7. API спецификация backend

Ниже — рекомендуемый REST API. Можно сделать и через tRPC/GraphQL, но для команды разработки REST обычно прозрачнее.

7.1. Auth / admin session

POST /api/admin/session/init

Инициализация Telegram Web App сессии.

Request:

{
  "telegram_user_id": 123456789,
  "init_data": "..."
}

Response:

{
  "ok": true,
  "token": "jwt_or_session_token",
  "user": {
    "id": 7,
    "name": "Анна",
    "role": "admin"
  }
}

GET /api/admin/me

Возвращает текущего сотрудника.

⸻

7.2. Clients

GET /api/clients

Фильтры:
    •    status
    •    tag
    •    search
    •    assigned_user_id
    •    has_booking
    •    date_from/date_to
    •    page/limit

GET /api/clients/:id

Карточка клиента.

Response:

{
  "id": 101,
  "name": "Мария",
  "telegram_user_id": 555,
  "username": "mariax",
  "phone": "+7999...",
  "status": "booking_in_progress",
  "preferred_staff": null,
  "tags": ["laser", "warm_lead"],
  "last_dialog_at": "2026-04-07T16:20:00Z"
}

PATCH /api/clients/:id

Изменение полей карточки.

POST /api/clients/:id/tags

Добавление тегов.

POST /api/clients/:id/note

Добавление заметки.

⸻

7.3. Dialogs

GET /api/dialogs

Список диалогов.

GET /api/dialogs/:id

Диалог + сообщения + текущий режим + AI flags.

POST /api/dialogs/:id/takeover

Перевод в manual.

Request:

{
  "assigned_user_id": 7,
  "reason": "complaint"
}

POST /api/dialogs/:id/return-to-auto

Возврат в auto.

POST /api/dialogs/:id/send-message

Ручная отправка сообщения клиенту.

Request:

{
  "text": "Добрый вечер! Подключилась администратор 😊",
  "split_mode": "single"
}

POST /api/dialogs/:id/ai-draft

Получить AI-черновик ответа без отправки.

⸻

7.4. Bookings

GET /api/bookings

Фильтры:
    •    date
    •    branch_id
    •    staff_id
    •    status

POST /api/bookings

Создание записи вручную.

Request:

{
  "client_id": 101,
  "service_id": 12,
  "staff_id": 3,
  "branch_id": 1,
  "start_at": "2026-04-09T12:00:00+03:00",
  "comment": "Первичный визит"
}

PATCH /api/bookings/:id

Изменение записи.

POST /api/bookings/:id/cancel

Отмена записи.

POST /api/bookings/:id/reschedule

Перенос записи.

GET /api/bookings/:id/history

История изменений статусов.

⸻

7.5. Scheduling

GET /api/schedule/slots

Подбор свободных окон.

Параметры:
    •    service_id
    •    branch_id
    •    staff_id optional
    •    date_from
    •    date_to

Response:

{
  "slots": [
    {
      "start_at": "2026-04-09T12:00:00+03:00",
      "end_at": "2026-04-09T13:30:00+03:00",
      "staff_id": 3
    },
    {
      "start_at": "2026-04-09T15:00:00+03:00",
      "end_at": "2026-04-09T16:30:00+03:00",
      "staff_id": 3
    }
  ]
}

POST /api/schedule/staff/:id/day

Обновление графика мастера.

POST /api/schedule/staff/:id/block

Блокировка интервала.

⸻

7.6. Services / staff / branches

GET /api/services

POST /api/services

PATCH /api/services/:id

GET /api/staff

POST /api/staff

PATCH /api/staff/:id

GET /api/branches

POST /api/branches

⸻

7.7. Knowledge base

GET /api/knowledge

POST /api/knowledge

PATCH /api/knowledge/:id

DELETE /api/knowledge/:id

Типы knowledge items:
    •    service_info
    •    faq
    •    policy
    •    contraindication
    •    promo
    •    tone_of_voice
    •    objection_handling
    •    escalation_rule

⸻

7.8. Analytics

GET /api/analytics/overview

Метрики:
    •    new_clients
    •    dialogs_total
    •    bookings_total
    •    conversion_to_booking
    •    avg_first_response_sec
    •    cancel_rate
    •    no_show_rate

GET /api/analytics/funnel

GET /api/analytics/services

GET /api/analytics/staff

GET /api/analytics/ai

⸻

7.9. Notifications

GET /api/notifications

POST /api/notifications/:id/read

⸻

7.10. System / logs

GET /api/audit-logs

GET /api/system/errors

GET /api/system/jobs

⸻

8. Webhook endpoints

8.1. Telegram webhook

POST /webhooks/telegram

Принимает Telegram updates.

Нужно обрабатывать:
    •    business connection updates
    •    incoming business messages
    •    edited business messages
    •    callback queries от admin bot
    •    web app data
    •    обычные служебные команды

Telegram Business docs и Bot API указывают на отдельные business-related обновления и методы для connected business bots.  ￼

8.2. Internal job callbacks

POST /internal/jobs/reminders

POST /internal/jobs/followups

⸻

9. AI orchestration contract

9.1. Вход в AI-router

{
  "client": {
    "id": 101,
    "name": "Мария",
    "status": "consulting",
    "tags": ["laser"]
  },
  "dialog": {
    "id": 88,
    "mode": "auto",
    "history": [
      {"role": "user", "text": "Сколько стоит лазер?"}
    ]
  },
  "message": {
    "text": "А на этой неделе можно записаться?"
  },
  "context": {
    "candidate_services": [12],
    "available_slots": [],
    "branch": "Центр"
  },
  "rules": {
    "medical_sensitive": true,
    "allow_humor": true,
    "max_message_len": 350
  }
}

9.2. Выход AI-router

{
  "decision": "reply",
  "intent": "booking",
  "risk_level": "medium",
  "should_escalate": false,
  "reply": {
    "split": true,
    "messages": [
      "Да, на этой неделе есть окна 😊",
      "Подскажите, вам удобнее ближе к вечеру или днём?"
    ]
  },
  "extracted_entities": {
    "service_id": 12,
    "desired_period": "this_week"
  },
  "next_action": "request_time_preference"
}

9.3. Возможные decision
    •    reply
    •    escalate
    •    ask_clarification
    •    draft_only
    •    no_reply

⸻

10. Rules engine

10.1. Жёсткие правила

Если срабатывает одно из них, AI не отвечает свободно:
    •    complaint
    •    refund
    •    adverse reaction
    •    legal threat
    •    request for manager
    •    suicidal / self-harm related content
    •    explicit medical contraindication conflict

10.2. Мягкие правила

AI может ответить, но в аккуратном режиме:
    •    price objection
    •    trust objection
    •    “дорого”
    •    “я подумаю”
    •    “а почему у вас так”

10.3. Stylistic rules
    •    не более 1-2 эмодзи на короткий ответ
    •    без спама знаками
    •    без кринжового “солнышко/дорогая”, если ToV этого не требует
    •    не больше 3 коротких сообщений подряд
    •    не имитировать намеренно безграмотность как основную механику

⸻

11. Экраны Web App

11.1. Экран 1 — Dashboard

Блоки:
    •    новые диалоги
    •    записи сегодня
    •    отмены сегодня
    •    диалоги на перехвате
    •    конверсия за 7 дней
    •    быстрые действия

11.2. Экран 2 — Диалоги

Слева список диалогов:
    •    имя
    •    статус
    •    последний месседж
    •    кто ведёт
    •    флаг риска

Справа:
    •    чат-лента
    •    AI suggestion
    •    кнопки:
    •    takeover
    •    return to auto
    •    send
    •    schedule
    •    client card

11.3. Экран 3 — Карточка клиента

Поля:
    •    имя / username / телефон
    •    теги
    •    статус
    •    история записей
    •    история сообщений
    •    комментарии
    •    тема staff group
    •    ближайший визит

11.4. Экран 4 — Записи / календарь

Виды:
    •    день
    •    неделя
    •    по мастерам
    •    по филиалам

Функции:
    •    создать
    •    перенести
    •    отменить
    •    отметить no-show
    •    отметить completed

11.5. Экран 5 — Услуги
    •    список услуг
    •    длительность
    •    цена
    •    доступные мастера
    •    требования / подготовка / противопоказания

11.6. Экран 6 — Мастера
    •    графики
    •    специализация
    •    услуги
    •    нагрузка
    •    статистика конверсии

11.7. Экран 7 — База знаний
    •    FAQ
    •    правила
    •    акции
    •    сценарии
    •    ToV
    •    стоп-темы

11.8. Экран 8 — Аналитика
    •    воронка
    •    конверсия
    •    top services
    •    отмены
    •    no-show
    •    AI handled vs human handled

11.9. Экран 9 — Настройки
    •    список сотрудников
    •    роли
    •    ai policies
    •    service hours
    •    reminder policies

⸻

12. SQL-схема, минимальный каркас

Ниже не полный production SQL, а рабочий skeleton.

create table roles (
  id bigserial primary key,
  code text unique not null,
  name text not null,
  permissions_json jsonb not null default '{}'::jsonb
);

create table users (
  id bigserial primary key,
  telegram_user_id bigint unique not null,
  full_name text not null,
  username text,
  role_id bigint not null references roles(id),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table clients (
  id bigserial primary key,
  telegram_user_id bigint unique not null,
  username text,
  full_name text,
  phone text,
  status text not null default 'new',
  source text,
  notes text,
  preferred_branch_id bigint,
  preferred_staff_id bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table dialogs (
  id bigserial primary key,
  client_id bigint not null references clients(id),
  business_connection_id text,
  telegram_chat_id bigint not null,
  mode text not null default 'auto',
  status text not null default 'new',
  assigned_user_id bigint references users(id),
  forum_topic_id bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table messages (
  id bigserial primary key,
  dialog_id bigint not null references dialogs(id),
  telegram_message_id bigint,
  direction text not null,
  sender_type text not null,
  content_type text not null default 'text',
  text_content text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table branches (
  id bigserial primary key,
  name text not null,
  address text,
  timezone text not null default 'Europe/Helsinki',
  is_active boolean not null default true
);

create table services (
  id bigserial primary key,
  name text not null,
  description text,
  duration_min integer not null,
  price_from numeric(10,2),
  price_to numeric(10,2),
  is_active boolean not null default true
);

create table staff_members (
  id bigserial primary key,
  full_name text not null,
  specialization text,
  branch_id bigint references branches(id),
  is_active boolean not null default true
);

create table staff_service_map (
  id bigserial primary key,
  staff_id bigint not null references staff_members(id),
  service_id bigint not null references services(id),
  unique (staff_id, service_id)
);

create table staff_schedules (
  id bigserial primary key,
  staff_id bigint not null references staff_members(id),
  start_at timestamptz not null,
  end_at timestamptz not null,
  is_available boolean not null default true
);

create table bookings (
  id bigserial primary key,
  client_id bigint not null references clients(id),
  service_id bigint not null references services(id),
  staff_id bigint references staff_members(id),
  branch_id bigint references branches(id),
  start_at timestamptz not null,
  end_at timestamptz not null,
  status text not null default 'pending',
  source text not null default 'telegram',
  comment text,
  created_by_user_id bigint references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table knowledge_items (
  id bigserial primary key,
  kind text not null,
  title text not null,
  content text not null,
  metadata_json jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table audit_logs (
  id bigserial primary key,
  actor_type text not null,
  actor_id text,
  action text not null,
  entity_type text not null,
  entity_id text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);


⸻

13. Очереди и фоновые jobs

Нужны отдельные jobs:
    •    send_staff_notification
    •    create_forum_topic
    •    sync_topic_messages
    •    generate_ai_reply
    •    send_booking_reminder
    •    send_followup_after_cancel
    •    rebuild_knowledge_embeddings
    •    daily_analytics_snapshot

⸻

14. Error handling

14.1. Ошибки Telegram

Если Telegram API не принял сообщение:
    •    писать в audit_logs
    •    ретраить 3 раза
    •    если неуспешно — уведомить staff

14.2. Ошибки AI

Если AI timeout / bad output:
    •    не отправлять сырой мусор клиенту
    •    fallback на safe template
    •    при необходимости эскалация человеку

14.3. Ошибки расписания

Если слот уже занят:
    •    не создавать booking
    •    отдать следующий доступный слот
    •    записать conflict event

⸻

15. Acceptance criteria для разработчика

Реализация считается завершённой, если:
    1.    backend принимает Telegram business updates;
    2.    система умеет отвечать от имени business account;
    3.    /admin доступен только сотрудникам;
    4.    Web App открывается и показывает CRM;
    5.    для нового клиента создаётся карточка и диалог;
    6.    для нового клиента создаётся тема в staff group;
    7.    сообщения клиента и системы дублируются в тему;
    8.    booking создаётся через Telegram flow;
    9.    перенос и отмена работают;
    10.    takeover переводит диалог в manual;
    11.    AI не отвечает в manual mode;
    12.    аналитика считает хотя бы базовую воронку;
    13.    все критические действия попадают в audit log.

⸻

16. Что я бы рекомендовал как реальный первый релиз

Не пытаться в первом релизе закрыть вообще всё. Самый сильный v1 такой:
    •    Telegram Business connected bot
    •    запись, перенос, отмена
    •    staff topics
    •    /admin + Web App
    •    клиенты, диалоги, записи
    •    knowledge base
    •    AI consultation + booking
    •    manual takeover
    •    reminders
    •    базовая аналитика

Это уже будет полноценный продукт, а не “MVP на коленке”.

Дальше могу собрать третью часть: готовый PRD/roadmap по спринтам на 4-6 недель или сразу выдать Cursor-ready prompt для разработки backend и админки.
