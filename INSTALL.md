# Installation

## Ubuntu host prerequisites

- Ubuntu Server with outbound network access;
- Docker Engine and the Docker Compose plugin;
- Git;
- DNS and TLS termination plan for the admin and subscription domain.

## Scripted install

Clone or download the repository installer and run:

```bash
bash scripts/install.sh <github-repository-url>
```

The installer clones into `/opt/vpnbotx` by default, creates `.env` from `.env.example`, generates
some random secrets, builds the Compose stack, runs migrations and shows service status.

Before production traffic:

1. Set `TELEGRAM_BOT_TOKEN`.
2. Replace `CREDENTIALS_ENCRYPTION_KEY` with a real Fernet-compatible key before storing 3X-UI
   credentials.
3. Set `FRONTEND_ORIGIN` and `SUBSCRIPTION_PUBLIC_BASE_URL` to real domains.
4. Configure TLS at the host proxy or replace the bundled Nginx config with the deployment policy.
5. Create the owner:

   ```bash
   docker compose -f docker-compose.prod.yml exec backend_api vpnbotx create-admin --role owner
   ```

## Manual install

```bash
git clone <github-repository-url> /opt/vpnbotx
cd /opt/vpnbotx
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend_api vpnbotx migrate
```

## Backups

```bash
./scripts/backup_db.sh
./scripts/restore_db.sh backups/vpnbotx-YYYYMMDDTHHMMSSZ.sql.gz
```

Keep database backups outside the Compose volumes and protect `.env` separately.

