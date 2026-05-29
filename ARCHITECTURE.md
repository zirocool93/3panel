# Архитектура

## Слои

```text
api / bot / cli / workers
        |
application services
        |
repositories и provider interfaces
        |
PostgreSQL / Redis / 3X-UI / payment APIs
```

API, Telegram-бот и worker entrypoints должны оставаться тонкими. Бизнес-правила живут в сервисах,
доступ к данным - в repositories, внешние панели и платежи - за provider interfaces.

## Модули текущего этапа

- `app/core` - конфигурация, security, logging, enum и permission policy;
- `app/api` - FastAPI entrypoint и admin endpoints;
- `app/bot` - aiogram entrypoint;
- `app/db` - SQLAlchemy модели, session и Alembic migrations;
- `app/services/panels` - контракт VPN panel provider;
- `app/services/system` - безопасные operational actions из админки;
- `app/workers` - Celery и scheduler;
- `frontend` - React admin shell;
- `scripts` - install, update, backup и restore flow.

## Таблицы текущего этапа

Первая миграция создаёт:

- `users`;
- `admin_users`;
- `admin_refresh_tokens`;
- `servers`;
- `server_groups`;
- `server_group_servers`;
- `tariffs`;
- `tariff_groups`;
- `tariff_group_tariffs`;
- `tariff_server_groups`;
- `vpn_subscriptions`;
- `vpn_subscription_nodes`.

Следующие миграции добавят orders, payments, balance ledger, promocodes, promo links, referrals,
broadcasts, notifications, audit logs и settings.

## Целевой lifecycle заказа

```text
draft -> pending_payment -> paid -> fulfilled
                     \-> expired | cancelled
```

Order фиксирует стоимость и назначение покупки. Payment хранит внешние платежные события и
идемпотентность обработки.

## Целевой lifecycle подписки

```text
pending -> active -> expired
        \-> provisioning_failed
active  -> disabled
```

`vpn_subscriptions` - коммерческая родительская подписка. `vpn_subscription_nodes` - клиенты на
конкретных VPN-серверах. Это даёт мультисерверную subscription-ссылку без дублирования заказа.

## Интеграция с панелями

`PanelProvider` задаёт контракт:

- создать и обновить клиента;
- удалить или отключить клиента;
- сбросить трафик;
- получить статистику;
- получить provider subscription URL.

`XuiProvider` будет первой реализацией. Специфичные payload 3X-UI не должны проникать в pricing,
orders и subscription lifecycle.

## Обновление из админки

Self-update - operational service, а не shell endpoint общего назначения. API принимает только
запрос на запуск заранее настроенного `scripts/admin_update.sh`. Скрипт берёт Git ref из `.env`,
делает backup, выполняет update flow и пишет лог в `var/`.

## Stage 2 lifecycle

The commerce lifecycle is now implemented as a backend service chain:

```text
User -> Order -> Payment -> Celery provisioning -> VpnSubscription -> /sub/{token}
```

Thin entrypoints call services:

- API routers validate auth/HTTP shape and delegate to services.
- Bot handlers call bot-facing facades and do not own business rules.
- Celery tasks only open a session and call `SubscriptionProvisioningService`.

Important services:

- `UserService` creates/updates Telegram users and handles start payload attribution.
- `TariffCatalogService` returns visible tariff DTOs and payment-method-specific prices.
- `OrderService` snapshots commercial terms into `orders`.
- `PaymentService` owns idempotent payment success/failure transitions.
- `TelegramStarsService` validates invoice payload and delegates success to `PaymentService`.
- `ServerSelectionService` chooses enabled, healthy, available servers/inbounds.
- `SubscriptionProvisioningService` creates or extends subscriptions and calls the panel provider.
- `SubscriptionService` powers `/sub/{token}`, expiry and future stats sync.

Payment idempotency is enforced by a unique `idempotency_key`, a partial unique index over non-empty `provider + external_payment_id`, and service checks that already-succeeded payments return without provisioning again. Provisioning idempotency stores the produced `subscription_id` in order metadata and reuses active subscriptions/nodes on retry.
