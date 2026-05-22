# Установка

## Требования к серверу

- Ubuntu Server с доступом в интернет;
- пользователь с `sudo`;
- DNS-домены для админки и subscription endpoint перед production-запуском;
- доступ к публичному GitHub-репозиторию или к вашему fork.

Установщик сам проверяет `git`, Docker и Compose. Если Docker отсутствует, он использует
официальный Docker install script. Для изолированных серверов установите Docker вручную заранее.

## Автоматическая установка

```bash
curl -fsSL https://raw.githubusercontent.com/zirocool93/3panel/main/scripts/install.sh -o install.sh
bash install.sh
```

Другой репозиторий можно передать аргументом:

```bash
bash install.sh https://github.com/<owner>/<repo>.git
```

По умолчанию проект размещается в `/opt/vpnbotx`. Путь можно изменить:

```bash
VPNBOTX_INSTALL_DIR=/srv/vpnbotx bash install.sh
```

Скрипт:

1. устанавливает `git` и Docker, если они отсутствуют;
2. клонирует Git checkout;
3. создаёт `.env` из `.env.example`;
4. генерирует пароль PostgreSQL и JWT secret;
5. создаёт каталоги `var/` и `backups/`;
6. собирает и запускает `docker-compose.prod.yml`;
7. выводит команду создания owner-админа.

## Настройка `.env`

Перед доступом пользователей заполните:

```env
TELEGRAM_BOT_TOKEN=
FRONTEND_ORIGIN=https://admin.example.com
SUBSCRIPTION_PUBLIC_BASE_URL=https://vpn.example.com
CREDENTIALS_ENCRYPTION_KEY=
```

`CREDENTIALS_ENCRYPTION_KEY` нужен до сохранения логинов и паролей 3X-UI. Секреты не должны
попадать в Git.

## Создание администратора

```bash
cd /opt/vpnbotx
docker compose -f docker-compose.prod.yml exec backend_api vpnbotx create-admin --role owner
```

## Ручная установка

```bash
git clone https://github.com/zirocool93/3panel.git /opt/vpnbotx
cd /opt/vpnbotx
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend_api vpnbotx create-admin --role owner
```

Миграции применяются при старте `backend_api`.

## Backup и restore

```bash
bash ./scripts/backup_db.sh
bash ./scripts/restore_db.sh backups/vpnbotx-YYYYMMDDTHHMMSSZ.sql.gz
```

Храните backups и `.env` отдельно от Docker volumes.

## TLS и reverse proxy

В репозитории есть базовый Nginx reverse proxy для Compose. Для production добавьте TLS на
внешнем proxy или расширьте конфигурацию под вашу схему сертификатов и доменов.
