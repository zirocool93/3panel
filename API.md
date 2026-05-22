# API

FastAPI exposes OpenAPI documentation at `/docs` in Stage 1.

## Implemented endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | process health |
| `POST` | `/api/auth/login` | admin access and refresh token pair |
| `POST` | `/api/auth/refresh` | refresh token rotation |
| `POST` | `/api/auth/logout` | refresh token revocation |
| `GET` | `/api/auth/me` | current admin profile |

## Planned endpoint groups

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

