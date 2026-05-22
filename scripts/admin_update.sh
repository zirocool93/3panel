#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${VPNBOTX_INSTALL_DIR:-/opt/vpnbotx}"
TARGET_REF="${1:-main}"
VAR_DIR="${VPNBOTX_VAR_DIR:-$INSTALL_DIR/var}"
LOCK_PATH="${ADMIN_UPDATE_LOCK_PATH:-$VAR_DIR/admin-update.lock}"
LOG_PATH="${ADMIN_UPDATE_LOG_PATH:-$VAR_DIR/admin-update.log}"
LOCK_HELD="${VPNBOTX_ADMIN_UPDATE_LOCK_HELD:-0}"

mkdir -p "$VAR_DIR"

if [[ "$LOCK_HELD" != "1" ]]; then
  if ! (set -o noclobber; printf '%s\n' "$$" > "$LOCK_PATH") 2>/dev/null; then
    echo "Update is already running: $LOCK_PATH"
    exit 1
  fi
fi

cleanup() {
  rm -f "$LOCK_PATH"
}
trap cleanup EXIT
cd "$INSTALL_DIR"

{
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Admin update started for ref $TARGET_REF"
  bash ./scripts/update.sh "$TARGET_REF"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Admin update finished"
} >> "$LOG_PATH" 2>&1
