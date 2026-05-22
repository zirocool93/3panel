# Обновление

## Обновление на сервере

```bash
cd /opt/vpnbotx
bash ./scripts/update.sh main
```

Скрипт:

1. вызывает `scripts/backup_db.sh`;
2. делает `git fetch` и fast-forward выбранного ref;
3. пересобирает контейнеры;
4. применяет Alembic-миграции;
5. запускает обновлённый Compose stack.

Для релизного deployment вместо `main` можно передать tag или release branch, если он совместим с
текущими миграциями.

## Обновление из web-админки

API:

- `GET /api/system/updates` - статус self-update и последние строки лога;
- `POST /api/system/updates` - запустить обновление.

Оба endpoint доступны только admin-пользователю с ролью `owner`.

Для включения добавьте в production `.env`:

```env
ADMIN_UPDATES_ENABLED=true
ADMIN_UPDATE_REF=main
ADMIN_UPDATE_COMMAND=/deployment/scripts/admin_update.sh
ADMIN_UPDATE_LOG_PATH=/deployment/var/admin-update.log
ADMIN_UPDATE_LOCK_PATH=/deployment/var/admin-update.lock
```

`ADMIN_UPDATE_REF` выбирается конфигурацией сервера. API не принимает произвольную команду или ref
из frontend.

## Права self-update

Production Compose монтирует в `backend_api`:

- checkout проекта как `/deployment`;
- `/var/run/docker.sock`.

Это позволяет скрипту из контейнера обновлять Git checkout, пересобирать контейнеры и применять
миграции. Фактически доступ к Docker socket даёт повышенные права на deployment host.

Оставьте `ADMIN_UPDATES_ENABLED=false`, если:

- админка не должна управлять deployment;
- обновления выполняет CI/CD;
- Docker socket нельзя передавать API-контейнеру по вашей security policy.

## Lock и логи

`scripts/admin_update.sh` использует lock-файл `var/admin-update.lock`, чтобы не запускать два
обновления одновременно. Лог пишется в `var/admin-update.log` и показывается на экране
`Обновление`.

## Откат

Откат приложения и откат схемы БД - разные операции. Не запускайте старый код поверх новой схемы
без проверки совместимости. Перед каждым update создаётся backup PostgreSQL; используйте его при
восстановлении deployment.
