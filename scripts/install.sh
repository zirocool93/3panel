#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REPO_URL="https://github.com/zirocool93/3panel.git"
REPO_URL="${1:-$DEFAULT_REPO_URL}"
INSTALL_DIR="${VPNBOTX_INSTALL_DIR:-/opt/vpnbotx}"

info() {
  printf '\033[1;34m[VPNBotX]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[VPNBotX]\033[0m %s\n' "$*" >&2
}

fail() {
  printf '\033[1;31m[VPNBotX]\033[0m %s\n' "$*" >&2
  exit 1
}

need_sudo() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    need_sudo docker "$@"
  fi
}

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker_cmd compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    fail "Docker Compose не найден."
  fi
}

ask_required() {
  local prompt="$1"
  local value=""
  while [[ -z "$value" ]]; do
    read -r -p "$prompt: " value
  done
  printf '%s' "$value"
}

ask_default() {
  local prompt="$1"
  local default="$2"
  local value=""
  read -r -p "$prompt [$default]: " value
  printf '%s' "${value:-$default}"
}

ask_secret() {
  local prompt="$1"
  local value=""
  while [[ -z "$value" ]]; do
    read -r -s -p "$prompt: " value
    printf '\n'
  done
  printf '%s' "$value"
}

ask_admin_password() {
  local password=""
  local confirmation=""
  while true; do
    password="$(ask_secret "Пароль первого администратора, минимум 8 символов")"
    confirmation="$(ask_secret "Повторите пароль администратора")"
    if [[ "$password" != "$confirmation" ]]; then
      warn "Пароли не совпадают."
      continue
    fi
    if [[ "${#password}" -lt 8 ]]; then
      warn "Пароль должен содержать минимум 8 символов."
      continue
    fi
    printf '%s' "$password"
    return 0
  done
}

detect_lan_url() {
  local ip=""
  ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  if [[ -z "$ip" ]]; then
    ip="127.0.0.1"
  fi
  printf 'http://%s' "$ip"
}

set_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  local escaped
  escaped="$(printf '%s' "$value" | sed -e 's/[\/&]/\\&/g')"
  if grep -q "^${key}=" "$file"; then
    sed -i "s/^${key}=.*/${key}=${escaped}/" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

check_ubuntu() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      warn "Целевая ОС - Ubuntu 24.04. Сейчас обнаружено: ${PRETTY_NAME:-unknown}."
    elif [[ "${VERSION_ID:-}" != "24.04" ]]; then
      warn "Рекомендуется Ubuntu 24.04. Сейчас обнаружено: ${PRETTY_NAME:-Ubuntu}."
    fi
  fi
}

install_system_packages() {
  if [[ "$(id -u)" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
    fail "Нужен sudo или запуск от root."
  fi

  local missing=()
  for binary in curl git openssl python3; do
    if ! command -v "$binary" >/dev/null 2>&1; then
      missing+=("$binary")
    fi
  done

  if [[ "${#missing[@]}" -gt 0 ]]; then
    info "Устанавливаю базовые пакеты: ${missing[*]}"
    need_sudo apt-get update
    need_sudo apt-get install -y ca-certificates curl git openssl python3
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    info "Docker и Docker Compose уже установлены."
    return 0
  fi

  info "Устанавливаю Docker Engine и Compose plugin."
  need_sudo apt-get update
  need_sudo apt-get install -y ca-certificates curl gnupg
  need_sudo install -m 0755 -d /etc/apt/keyrings

  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | need_sudo tee /etc/apt/keyrings/docker.asc >/dev/null
    need_sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local codename
  codename="$(
    . /etc/os-release
    printf '%s' "${VERSION_CODENAME:-noble}"
  )"

  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "$codename" | need_sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  need_sudo apt-get update
  need_sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  need_sudo systemctl enable --now docker
}

ensure_swap() {
  local mem_total_kb swap_total_kb swap_path
  mem_total_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
  swap_total_kb="$(awk '/SwapTotal/ {print $2}' /proc/meminfo)"
  swap_path="${VPNBOTX_SWAP_PATH:-/swapfile}"

  if (( mem_total_kb >= 3000000 || swap_total_kb >= 1000000 )); then
    return 0
  fi

  warn "На сервере мало RAM и swap. Создаю swap 2G для Docker build."
  if [[ ! -f "$swap_path" ]]; then
    need_sudo fallocate -l 2G "$swap_path" || need_sudo dd if=/dev/zero of="$swap_path" bs=1M count=2048
    need_sudo chmod 600 "$swap_path"
    need_sudo mkswap "$swap_path"
  fi

  if ! swapon --show=NAME | grep -qx "$swap_path"; then
    need_sudo swapon "$swap_path"
  fi

  if ! grep -q "^${swap_path} " /etc/fstab; then
    echo "$swap_path none swap sw 0 0" | need_sudo tee -a /etc/fstab >/dev/null
  fi
}

collect_initial_data() {
  info "Первичная настройка."
  TELEGRAM_BOT_TOKEN_VALUE="$(ask_required "TELEGRAM_BOT_TOKEN")"
  ADMIN_EMAIL_VALUE="$(ask_required "Email первого администратора")"
  ADMIN_PASSWORD_VALUE="$(ask_admin_password)"

  echo
  echo "Выберите режим доступа к web-панели:"
  echo "  1) Домен или внешний reverse proxy"
  echo "  2) Без домена, только локальная сеть"
  read -r -p "Режим [1/2, по умолчанию 2]: " DEPLOYMENT_MODE
  DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-2}"

  if [[ "$DEPLOYMENT_MODE" == "1" ]]; then
    ADMIN_PUBLIC_URL_VALUE="$(ask_required "Публичный URL админки, например https://admin.example.com")"
    SUBSCRIPTION_PUBLIC_URL_VALUE="$(ask_default "Публичный subscription URL" "$ADMIN_PUBLIC_URL_VALUE")"
    FRONTEND_ORIGIN_VALUE="$ADMIN_PUBLIC_URL_VALUE"
    REVERSE_PROXY_HINT="true"
  else
    local detected_url
    detected_url="$(detect_lan_url)"
    ADMIN_PUBLIC_URL_VALUE="$(ask_default "URL web-панели в локальной сети" "$detected_url")"
    SUBSCRIPTION_PUBLIC_URL_VALUE="$(ask_default "Subscription URL" "$ADMIN_PUBLIC_URL_VALUE")"
    FRONTEND_ORIGIN_VALUE="$ADMIN_PUBLIC_URL_VALUE,http://localhost,http://127.0.0.1"
    REVERSE_PROXY_HINT="false"
  fi

  ENABLE_ADMIN_UPDATES_VALUE="$(ask_default "Разрешить обновление из админ-панели? yes/no" "no")"
  if [[ "$ENABLE_ADMIN_UPDATES_VALUE" =~ ^([Yy][Ee][Ss]|[Yy]|да|Да)$ ]]; then
    ADMIN_UPDATES_ENABLED_VALUE="true"
  else
    ADMIN_UPDATES_ENABLED_VALUE="false"
  fi
}

write_env_file() {
  local env_file="$INSTALL_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    cp "$INSTALL_DIR/.env.example" "$env_file"
  else
    cp "$env_file" "$env_file.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  fi

  local postgres_password jwt_secret encryption_key webhook_secret
  postgres_password="$(python3 - <<'PY'
from secrets import token_urlsafe
print(token_urlsafe(24))
PY
)"
  jwt_secret="$(python3 - <<'PY'
from secrets import token_urlsafe
print(token_urlsafe(48))
PY
)"
  encryption_key="$(python3 - <<'PY'
import base64
from secrets import token_bytes
print(base64.urlsafe_b64encode(token_bytes(32)).decode())
PY
)"
  webhook_secret="$(python3 - <<'PY'
from secrets import token_urlsafe
print(token_urlsafe(32))
PY
)"

  set_env_value "ENVIRONMENT" "production" "$env_file"
  set_env_value "POSTGRES_PASSWORD" "$postgres_password" "$env_file"
  set_env_value "DATABASE_URL" "postgresql+asyncpg://vpnbotx:${postgres_password}@postgres:5432/vpnbotx" "$env_file"
  set_env_value "SYNC_DATABASE_URL" "postgresql+psycopg://vpnbotx:${postgres_password}@postgres:5432/vpnbotx" "$env_file"
  set_env_value "JWT_SECRET_KEY" "$jwt_secret" "$env_file"
  set_env_value "CREDENTIALS_ENCRYPTION_KEY" "$encryption_key" "$env_file"
  set_env_value "TELEGRAM_BOT_TOKEN" "$TELEGRAM_BOT_TOKEN_VALUE" "$env_file"
  set_env_value "TELEGRAM_WEBHOOK_SECRET" "$webhook_secret" "$env_file"
  set_env_value "FRONTEND_ORIGIN" "$FRONTEND_ORIGIN_VALUE" "$env_file"
  set_env_value "SUBSCRIPTION_PUBLIC_BASE_URL" "$SUBSCRIPTION_PUBLIC_URL_VALUE" "$env_file"
  set_env_value "ADMIN_UPDATES_ENABLED" "$ADMIN_UPDATES_ENABLED_VALUE" "$env_file"
}

create_owner_admin() {
  info "Создаю первого администратора."
  if ! docker_compose -f docker-compose.prod.yml exec -T backend_api \
    env VPNBOTX_ADMIN_PASSWORD="$ADMIN_PASSWORD_VALUE" \
    vpnbotx create-admin --email "$ADMIN_EMAIL_VALUE" --role owner; then
    warn "Администратор не создан. Возможно, такой email уже существует."
  fi
}

wait_for_backend() {
  info "Ожидаю готовности backend_api."
  for _ in $(seq 1 60); do
    if docker_compose -f docker-compose.prod.yml exec -T backend_api \
      python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  fail "backend_api не стал доступен за 120 секунд. Проверьте docker compose logs backend_api."
}

main() {
  check_ubuntu
  install_system_packages
  install_docker
  ensure_swap
  collect_initial_data

  need_sudo mkdir -p "$INSTALL_DIR"
  need_sudo chown "$USER":"$USER" "$INSTALL_DIR"

  if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    info "Клонирую $REPO_URL в $INSTALL_DIR."
    git clone "$REPO_URL" "$INSTALL_DIR"
  else
    info "Git checkout уже существует: $INSTALL_DIR."
  fi

  cd "$INSTALL_DIR"
  mkdir -p var backups
  chmod +x scripts/*.sh
  write_env_file

  info "Собираю и запускаю Docker Compose."
  docker_compose -f docker-compose.prod.yml up -d --build
  wait_for_backend
  create_owner_admin
  docker_compose -f docker-compose.prod.yml ps

  echo
  info "VPNBotX установлен."
  echo "Каталог: $INSTALL_DIR"
  echo "Web-панель: $ADMIN_PUBLIC_URL_VALUE"
  echo "Subscription base URL: $SUBSCRIPTION_PUBLIC_URL_VALUE"
  if [[ "$REVERSE_PROXY_HINT" == "true" ]]; then
    echo "Reverse proxy: направьте внешний proxy на этот сервер, порт 80."
  else
    echo "Локальный режим: откройте web-панель из вашей LAN."
  fi
}

main "$@"
