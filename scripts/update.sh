#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${VPNBOTX_INSTALL_DIR:-/opt/vpnbotx}"
TARGET_REF="${1:-main}"

cd "$INSTALL_DIR"
./scripts/backup_db.sh
git fetch --tags origin
git checkout "$TARGET_REF"
git pull --ff-only origin "$TARGET_REF" || true
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm backend_api vpnbotx migrate
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps

