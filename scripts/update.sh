#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${VPNBOTX_INSTALL_DIR:-/opt/vpnbotx}"
TARGET_REF="${1:-main}"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

cd "$INSTALL_DIR"
bash ./scripts/backup_db.sh
git fetch --tags origin
git checkout "$TARGET_REF"
git pull --ff-only origin "$TARGET_REF"
docker_compose -f docker-compose.prod.yml build
docker_compose -f docker-compose.prod.yml run --rm backend_api vpnbotx migrate
docker_compose -f docker-compose.prod.yml up -d
docker_compose -f docker-compose.prod.yml restart nginx
docker_compose -f docker-compose.prod.yml ps
