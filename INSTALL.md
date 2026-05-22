# Установка на Ubuntu 24.04

## Что делает установщик

`scripts/install.sh` предназначен для первичного разворачивания VPNBotX на Ubuntu Server 24.04.

Он проверяет и устанавливает необходимые компоненты:

- `sudo`, если запуск не от root;
- `curl`;
- `git`;
- `openssl`;
- `python3`;
- Docker Engine;
- Docker Compose plugin.

Если Docker уже установлен, скрипт не переустанавливает его. Если Docker установлен без Compose
plugin, установщик добавит официальный Docker APT repository и поставит недостающие пакеты.

## Быстрая установка

```bash
curl -fsSL https://raw.githubusercontent.com/zirocool93/3panel/main/scripts/install.sh -o install.sh
bash install.sh
```

По умолчанию используется репозиторий:

```text
https://github.com/zirocool93/3panel.git
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

## Данные, которые запрашиваются при установке

Установщик интерактивно спросит:

- `TELEGRAM_BOT_TOKEN`;
- email первого администратора;
- пароль первого администратора;
- режим доступа к web-панели;
- публичный URL админки или локальный LAN URL;
- subscription base URL;
- разрешать ли обновление из админ-панели.

Пароль администратора не сохраняется в `.env`. Он используется только для создания owner-аккаунта.

## Режимы доступа к web-панели

### 1. Домен или внешний reverse proxy

Выбирайте этот режим, если web-панель будет открываться по домену, например:

```text
https://admin.example.com
```

Внешний reverse proxy должен направлять трафик на сервер с VPNBotX, порт `80`.
Backend запускается с `--proxy-headers`, поэтому может работать за proxy, который передаёт
`X-Forwarded-For` и `X-Forwarded-Proto`.

Пример внешнего Nginx upstream:

```nginx
location / {
    proxy_pass http://127.0.0.1:80;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 2. Без домена, только локальная сеть

Выбирайте этот режим, если админка должна быть доступна только внутри LAN.
Скрипт предложит URL вида:

```text
http://192.168.1.10
```

Этот URL будет записан в `FRONTEND_ORIGIN` и `SUBSCRIPTION_PUBLIC_BASE_URL`.

## Что создаётся автоматически

После ответов установщик:

1. клонирует Git checkout в директорию установки;
2. создаёт `.env`;
3. генерирует:
   - пароль PostgreSQL;
   - JWT secret;
   - `CREDENTIALS_ENCRYPTION_KEY`;
   - `TELEGRAM_WEBHOOK_SECRET`;
4. создаёт каталоги `var/` и `backups/`;
5. собирает и запускает `docker-compose.prod.yml`;
6. ждёт готовности `backend_api`;
7. создаёт первого администратора с ролью `owner`.

## Важные файлы

```text
/opt/vpnbotx/.env
/opt/vpnbotx/docker-compose.prod.yml
/opt/vpnbotx/var/admin-update.log
/opt/vpnbotx/backups/
```

`.env` содержит секреты и не должен попадать в Git.

## Обновление после установки

```bash
cd /opt/vpnbotx
bash ./scripts/update.sh main
```

Если при установке включено обновление из админ-панели, owner сможет запустить этот же controlled
update flow из раздела `Обновление`.

## Backup и restore

```bash
cd /opt/vpnbotx
bash ./scripts/backup_db.sh
bash ./scripts/restore_db.sh backups/vpnbotx-YYYYMMDDTHHMMSSZ.sql.gz
```

Храните backups отдельно от Docker volumes.

