# Установка на Ubuntu 24.04

## Поддерживаемый сценарий

Целевая ОС внутри сервера или контейнера: **Ubuntu 24.04**.

Установка поддерживает:

- обычный VPS/VM;
- Proxmox LXC контейнер, если включены нужные возможности контейнера.

## Минимальные требования

Минимум:

- CPU: 2 vCPU;
- RAM: 2 GB;
- Disk: 12 GB свободного места;
- Ubuntu 24.04;
- доступ в интернет;
- root или пользователь с `sudo`.

Рекомендовано:

- CPU: 2+ vCPU;
- RAM: 3-4 GB;
- swap: 1-2 GB;
- Disk: 20 GB.

Frontend собирается через Node/Vite. На малых VPS ошибка `exit code 137` почти всегда означает,
что процесс был убит из-за нехватки RAM/swap.

## Важно для Proxmox LXC

В LXC контейнере обычно нельзя выполнить `swapon` изнутри контейнера. Поэтому установщик больше не
пытается создавать swap внутри LXC. Если ресурсов недостаточно, он остановится и покажет, что нужно
добавить на Proxmox host.

Для LXC нужны:

- Ubuntu 24.04 template;
- RAM минимум 2 GB, лучше 3-4 GB;
- swap/memory swap на уровне Proxmox;
- disk минимум 12 GB;
- 2 vCPU;
- включённый nesting;
- включённый keyctl.

На Proxmox host:

```bash
pct set <CTID> -features nesting=1,keyctl=1
```

Если контейнер unprivileged и Docker не стартует, проверьте настройки LXC. Для самого простого
production-развёртывания Docker внутри LXC обычно проще запускать в privileged LXC или использовать
обычную VM.

Если установка сообщает, что не хватает RAM/swap:

1. остановите контейнер;
2. увеличьте RAM до 3-4 GB;
3. добавьте swap/memory swap в настройках CT;
4. запустите контейнер;
5. повторите установку.

## Автоматическая установка

```bash
curl -fsSL https://raw.githubusercontent.com/zirocool93/3panel/main/scripts/install.sh -o install.sh
bash install.sh
```

Другой fork можно передать аргументом:

```bash
bash install.sh https://github.com/<owner>/<repo>.git
```

Путь установки по умолчанию:

```text
/opt/vpnbotx
```

Изменить путь:

```bash
VPNBOTX_INSTALL_DIR=/srv/vpnbotx bash install.sh
```

## Что проверяет установщик

Установщик проверяет:

- версию Ubuntu;
- наличие `sudo`, если запуск не от root;
- `curl`;
- `git`;
- `openssl`;
- `python3`;
- Docker Engine;
- Docker Compose plugin;
- CPU;
- RAM;
- swap;
- свободное место на диске;
- доступность Docker daemon.

Если минимальные требования не выполнены, установка останавливается и выводит конкретные действия,
которые нужно выполнить.

## Данные, которые запрашиваются

Установщик спросит:

- `TELEGRAM_BOT_TOKEN`;
- email первого администратора;
- пароль первого администратора;
- режим доступа к web-панели;
- публичный URL админки или локальный LAN URL;
- subscription base URL;
- разрешать ли обновление из админ-панели.

Пароль администратора не сохраняется в `.env`. Он используется только для создания owner-аккаунта.

## Режимы доступа к web-панели

### Домен или внешний reverse proxy

Выбирайте этот режим, если web-панель будет открываться по домену:

```text
https://admin.example.com
```

Внешний reverse proxy должен направлять трафик на сервер с VPNBotX, порт `80`.
Backend запускается с `--proxy-headers`, поэтому учитывает `X-Forwarded-For` и
`X-Forwarded-Proto`.

Пример внешнего Nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:80;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Без домена, только локальная сеть

Выбирайте этот режим, если админка должна быть доступна только внутри LAN.
Скрипт предложит URL вида:

```text
http://192.168.1.10
```

Этот URL будет записан в `FRONTEND_ORIGIN` и `SUBSCRIPTION_PUBLIC_BASE_URL`.

## Что создаётся автоматически

После ответов установщик:

1. клонирует Git checkout;
2. создаёт `.env`;
3. генерирует пароль PostgreSQL;
4. генерирует JWT secret;
5. генерирует `CREDENTIALS_ENCRYPTION_KEY`;
6. генерирует `TELEGRAM_WEBHOOK_SECRET`;
7. создаёт `var/` и `backups/`;
8. собирает и запускает `docker-compose.prod.yml`;
9. ждёт готовности `backend_api`;
10. создаёт первого администратора с ролью `owner`.

## Важные файлы

```text
/opt/vpnbotx/.env
/opt/vpnbotx/docker-compose.prod.yml
/opt/vpnbotx/var/admin-update.log
/opt/vpnbotx/backups/
```

`.env` содержит секреты и не должен попадать в Git.

## Обновление

```bash
cd /opt/vpnbotx
bash ./scripts/update.sh main
```

Если при установке включено обновление из админ-панели, owner сможет запустить controlled update
flow из раздела `Обновление`.

## Backup и restore

```bash
cd /opt/vpnbotx
bash ./scripts/backup_db.sh
bash ./scripts/restore_db.sh backups/vpnbotx-YYYYMMDDTHHMMSSZ.sql.gz
```

Храните backups отдельно от Docker volumes.

