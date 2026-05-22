# VPNBotX

`VPNBotX` - open-source проект для продажи VPN-доступа через Telegram-бота и web-админку.
Первый провайдер VPN-панели - `3X-UI`. Архитектура оставляет место для Marzban, Hiddify и других
панелей без переноса бизнес-логики в интеграционный слой.

## Состояние разработки

Проект разрабатывается по этапам. На текущем этапе в репозитории есть:

- FastAPI API с healthcheck и JWT-авторизацией web-админки;
- aiogram entrypoint Telegram-бота с командой `/start`;
- SQLAlchemy 2 модели и первая Alembic-миграция для пользователей, админов, серверов, тарифов и
  подписок;
- Celery worker и scheduler на Redis;
- React, TypeScript, Vite и Ant Design каркас админ-панели;
- Docker Compose для локального и production-shaped запуска;
- скрипты автоматической установки, обновления, backup и restore PostgreSQL;
- запуск обновления из админ-панели для owner-роли при явном включении deployment-настроек.

Интеграция с API `3X-UI`, платежи, баланс, выдача ключей, subscription endpoint, промо и
рефералы добавляются на следующих этапах.

## Быстрый локальный запуск

1. Создайте файл окружения:

   ```bash
   cp .env.example .env
   ```

2. Задайте в `.env` значения:
   - `POSTGRES_PASSWORD`;
   - `DATABASE_URL`;
   - `SYNC_DATABASE_URL`;
   - `JWT_SECRET_KEY`;
   - `CREDENTIALS_ENCRYPTION_KEY`.

3. Запустите стек:

   ```bash
   docker compose up --build
   ```

4. Создайте первого владельца:

   ```bash
   docker compose exec backend_api vpnbotx create-admin --role owner
   ```

5. Откройте:
   - web-интерфейс через Nginx: `http://localhost`;
   - healthcheck API: `http://localhost/health`;
   - OpenAPI: `http://localhost/docs`.

Если `TELEGRAM_BOT_TOKEN` пустой, контейнер бота стартует без polling.

## Автоматическая установка на Ubuntu 24.04

Для Ubuntu Server 24.04 предусмотрен интерактивный установщик:

```bash
curl -fsSL https://raw.githubusercontent.com/zirocool93/3panel/main/scripts/install.sh -o install.sh
bash install.sh
```

Он проверяет наличие `git`, `curl`, `python3`, Docker Engine и Docker Compose plugin, при
необходимости устанавливает недостающие компоненты, затем запрашивает:

- `TELEGRAM_BOT_TOKEN`;
- email и пароль первого администратора;
- режим доступа к web-панели: домен/reverse proxy или локальная сеть;
- URL админки и subscription endpoint;
- включать ли обновление из админ-панели.

После этого скрипт создаёт `.env`, генерирует секреты, запускает production Compose и создаёт
owner-админа.

Подробности - в [INSTALL.md](INSTALL.md).

## Обновление

Обновление с сервера:

```bash
cd /opt/vpnbotx
bash ./scripts/update.sh main
```

Перед обновлением выполняется backup PostgreSQL, затем подтягивается Git ref, собираются контейнеры,
применяются Alembic-миграции и перезапускается Compose.

### Обновление из админ-панели

Экран `Обновление` доступен в каркасе админки. Запуск обновления разрешён только owner-роли и
только когда в `.env` включено:

```env
ADMIN_UPDATES_ENABLED=true
ADMIN_UPDATE_REF=main
```

Production Compose монтирует checkout проекта и Docker socket в `backend_api`, чтобы update API
мог запустить контролируемый скрипт `scripts/admin_update.sh`. Это повышенные права на хосте.
Не включайте self-update, если deployment должен быть изолирован от Docker daemon.

Подробности - в [UPGRADE.md](UPGRADE.md).

## Сервисы

| Сервис | Назначение |
| --- | --- |
| `backend_api` | FastAPI, OpenAPI, auth, будущие admin/public endpoints |
| `telegram_bot` | aiogram runtime |
| `worker` | Celery задачи |
| `scheduler` | Celery Beat |
| `postgres` | основная БД |
| `redis` | очередь, брокер и кэш |
| `frontend` | web-админка |
| `nginx` | reverse proxy |

## Локальные проверки

```bash
pip install ".[dev]"
ruff check app tests
mypy app
pytest
cd frontend && npm install && npm run build
```

## Документация

- [INSTALL.md](INSTALL.md) - установка на сервер;
- [UPGRADE.md](UPGRADE.md) - обновления и self-update;
- [ARCHITECTURE.md](ARCHITECTURE.md) - модули, БД и жизненные циклы;
- [API.md](API.md) - текущие и планируемые API endpoints.
