# VPNBotX

VPNBotX is an open-source Telegram sales bot and web admin foundation for VPN access managed
through 3X-UI. The repository is developed in stages so commercial flows, VPN provisioning and
admin operations land on a testable deployment base.

## Stage 1 scope

Stage 1 provides:

- FastAPI API with health checks and web-admin JWT authentication;
- aiogram bot entrypoint with `/start`;
- SQLAlchemy 2 models and the first Alembic migration for users, admins, servers, tariffs and
  subscription records;
- Celery worker and scheduler skeleton backed by Redis;
- React, TypeScript, Vite and Ant Design admin shell;
- Docker Compose for local and production-shaped deployment;
- GitHub CI, install/update scripts, PostgreSQL backup and restore scripts.

The 3X-UI HTTP adapter, orders, payments, subscription rendering and full admin modules are added
in later stages described in [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick start

1. Create the environment file.

   ```bash
   cp .env.example .env
   ```

2. Set at least `POSTGRES_PASSWORD`, `DATABASE_URL`, `SYNC_DATABASE_URL`, `JWT_SECRET_KEY` and
   `CREDENTIALS_ENCRYPTION_KEY` in `.env`.
3. Start the stack.

   ```bash
   docker compose up --build
   ```

4. Create the first owner account.

   ```bash
   docker compose exec backend_api vpnbotx create-admin --role owner
   ```

5. Open the reverse proxy at `http://localhost` or the API health check at
   `http://localhost/health`.

The bot container starts without polling when `TELEGRAM_BOT_TOKEN` is empty.

## Services

| Service | Purpose |
| --- | --- |
| `backend_api` | FastAPI, OpenAPI, auth and future admin/public endpoints |
| `telegram_bot` | aiogram runtime |
| `worker` | Celery jobs |
| `scheduler` | Celery Beat schedules |
| `postgres` | application database |
| `redis` | broker and cache foundation |
| `frontend` | admin SPA |
| `nginx` | reverse proxy |

## Local checks

```bash
pip install ".[dev]"
ruff check app tests
mypy app
pytest
cd frontend && npm install && npm run build
```

## Deployment

Production deployment is expected to use a GitHub checkout on the server:

```bash
curl -fsSL <repository-raw-install-script-url> -o install.sh
bash install.sh <github-repository-url>
```

The repository contains deployment scripts under `scripts/`. Review [INSTALL.md](INSTALL.md) and
[UPGRADE.md](UPGRADE.md) before using them on a live server.

