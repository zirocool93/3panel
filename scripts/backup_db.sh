#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${VPNBOTX_BACKUP_DIR:-$ROOT_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

mkdir -p "$BACKUP_DIR"
cd "$ROOT_DIR"
docker_compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-vpnbotx}" "${POSTGRES_DB:-vpnbotx}" | gzip > "$BACKUP_DIR/vpnbotx-$STAMP.sql.gz"
echo "$BACKUP_DIR/vpnbotx-$STAMP.sql.gz"
