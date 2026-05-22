# API

FastAPI публикует OpenAPI на `/docs`.

## Реализованные endpoints

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/health` | healthcheck процесса |
| `POST` | `/api/auth/login` | access и refresh JWT для web-админки |
| `POST` | `/api/auth/refresh` | ротация refresh token |
| `POST` | `/api/auth/logout` | отзыв refresh token |
| `GET` | `/api/auth/me` | текущий admin-пользователь |
| `GET` | `/api/system/updates` | статус self-update для owner |
| `POST` | `/api/system/updates` | запуск self-update для owner |

## Планируемые endpoint-группы

- `/api/dashboard`
- `/api/users`
- `/api/servers`
- `/api/server-groups`
- `/api/tariffs`
- `/api/subscriptions`
- `/api/orders`
- `/api/payments`
- `/api/promocodes`
- `/api/promo-links`
- `/api/referrals`
- `/api/broadcasts`
- `/api/settings`
- `/api/audit-logs`
- `/sub/{token}`

## Self-update

`POST /api/system/updates` не принимает shell-команду и Git ref из запроса. Команда и ref читаются
из deployment settings:

- `ADMIN_UPDATE_COMMAND`;
- `ADMIN_UPDATE_REF`;
- `ADMIN_UPDATE_LOG_PATH`;
- `ADMIN_UPDATE_LOCK_PATH`.

Endpoint возвращает `202 Accepted`, когда background update process запущен.

