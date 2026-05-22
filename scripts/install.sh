#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-}"
INSTALL_DIR="${VPNBOTX_INSTALL_DIR:-/opt/vpnbotx}"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: scripts/install.sh <github-repository-url>"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine and rerun this script."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required."
  exit 1
fi

sudo mkdir -p "$INSTALL_DIR"
sudo chown "$USER":"$USER" "$INSTALL_DIR"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  python3 - <<'PY'
from pathlib import Path
from secrets import token_urlsafe

path = Path(".env")
content = path.read_text()
postgres_password = token_urlsafe(24)
content = content.replace("POSTGRES_PASSWORD=change-me", f"POSTGRES_PASSWORD={postgres_password}")
content = content.replace(
    "DATABASE_URL=postgresql+asyncpg://vpnbotx:change-me@postgres:5432/vpnbotx",
    f"DATABASE_URL=postgresql+asyncpg://vpnbotx:{postgres_password}@postgres:5432/vpnbotx",
)
content = content.replace(
    "SYNC_DATABASE_URL=postgresql+psycopg://vpnbotx:change-me@postgres:5432/vpnbotx",
    f"SYNC_DATABASE_URL=postgresql+psycopg://vpnbotx:{postgres_password}@postgres:5432/vpnbotx",
)
content = content.replace(
    "JWT_SECRET_KEY=replace-with-a-long-random-secret-before-production",
    f"JWT_SECRET_KEY={token_urlsafe(48)}",
)
path.write_text(content)
PY
  echo "Created .env. Set TELEGRAM_BOT_TOKEN, domains and encryption key before production use."
fi

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend_api vpnbotx migrate
docker compose -f docker-compose.prod.yml ps
echo "VPNBotX installed in $INSTALL_DIR."
