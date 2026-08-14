# Vape bazar Store Manager

> Русский ниже · [English version](#english)

Telegram-магазин с ботом, административной панелью, каналом товаров и мобильным Mini App. Система рассчитана на каталог электронных сигарет и сопутствующих товаров, но может быть адаптирована под другой магазин.

![Vape bazar Store Manager](assets/readme/hero.png)

## Русский

### Возможности

- каталог в Telegram-боте и Mini App;
- категории: POD-системы, жидкости, картриджи и испарители, снюс и пластинки, одноразовые электронные устройства;
- добавление товара через пошаговый сценарий администратора;
- количество, состояние нового или бывшего в употреблении товара, цена, скидка, описание и до пяти фотографий;
- публикация в бот, в Telegram-канал или одновременно в оба места;
- архив товаров с восстановлением остатков;
- поиск, сортировка, избранное и корзина;
- оформление заказов из Telegram Mini App;
- обработка заказов кнопками «Оставить заказ» и «Куплен»;
- PostgreSQL, Redis, FastAPI, aiogram, React, Caddy и Docker Compose;
- автоматические HTTPS-сертификаты через Caddy.

### Архитектура

| Компонент | Назначение |
| --- | --- |
| `bot` | Telegram-бот и административные сценарии на aiogram |
| `backend` | FastAPI API для каталога, медиа, Telegram WebApp и заказов |
| `web` | React Mini App и Caddy reverse proxy |
| `postgres` | товары, пользователи, заказы и журнал действий |
| `redis` | хранилище состояний Telegram-бота |
| `migrate` | применение миграций Alembic перед запуском |

### Требования

- Ubuntu 22.04 или новее;
- домен с A-записью, направленной на VPS;
- открытые TCP-порты `80` и `443`;
- SSH-доступ по ключу;
- Telegram-бот, созданный через `@BotFather`;
- Telegram-канал товаров и, при необходимости, отдельный канал заказов.

Рекомендуется выделить не менее 1 ГБ RAM, 1 vCPU и 10 ГБ диска.

### 1. Подготовка Telegram

1. Создайте бота через `@BotFather` и сохраните токен только в менеджере секретов или серверном `.env`.
2. Добавьте бота администратором в канал товаров с правами публикации и редактирования сообщений.
3. Если используется отдельный канал заказов, добавьте бота туда с правом отправки сообщений.
4. Получите числовой Telegram ID администратора и ID каналов.
5. После развёртывания настройте Menu Button/Mini App URL в BotFather: `https://your-domain.example/app`.

### 2. Подготовка VPS

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
less /tmp/get-docker.sh
sudo sh /tmp/get-docker.sh
sudo systemctl enable --now docker
docker compose version
```

Перед выполнением установочного скрипта Docker обязательно просмотрите его содержимое. Для production предпочтительнее официальный Docker apt-репозиторий с закреплённой версией пакетов.

### 3. Клонирование

```bash
sudo install -d -m 755 /opt/vape-bazar-store
sudo chown "$USER":"$USER" /opt/vape-bazar-store
git clone https://github.com/YOUR_USERNAME/vape-bazar-store.git /opt/vape-bazar-store
cd /opt/vape-bazar-store
```

### 4. Переменные окружения

```bash
cp .env.production.example .env
chmod 600 .env
openssl rand -hex 32
nano .env
```

Обязательные параметры:

```dotenv
BOT_TOKEN=replace_with_botfather_token
ADMIN_IDS=123456789
CHANNEL_ID=-1001234567890
ORDER_CHANNEL_ID=-1001234567891

SUPPORT_USERNAME=manager_username
SUPPORT_URL=https://t.me/manager_username
REVIEWS_URL=https://t.me/reviews_channel
TIKTOK_URL=https://www.tiktok.com/@your_store
LOGISTICS_URL=https://t.me/your_channel/1

MINI_APP_URL=https://your-domain.example/app
CADDY_SITE_ADDRESS=your-domain.example

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=store_manager
POSTGRES_USER=store_manager
POSTGRES_PASSWORD=replace_with_generated_64_character_password

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
LOG_LEVEL=INFO
```

Никогда не добавляйте `.env`, токены, пароли, приватные SSH-ключи или дампы базы в Git.

### 5. DNS и firewall

Создайте A-запись домена на IP вашего VPS. Затем разрешите только нужные входящие порты:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

PostgreSQL и Redis не должны публиковаться в интернет.

### 6. Запуск

```bash
cd /opt/vape-bazar-store
docker compose config
docker compose build --pull
docker compose up -d
docker compose ps
```

Проверка:

```bash
curl -fsS https://your-domain.example/api/health
docker compose logs --tail=100 bot backend web
```

Ожидаемый ответ health check:

```json
{"ok":true}
```

### 7. Обновление

```bash
cd /opt/vape-bazar-store
git pull --ff-only
docker compose build --pull
docker compose up -d
docker compose ps
```

Перед обновлением создайте резервную копию базы.

### 8. Резервное копирование

```bash
mkdir -p backups
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > "backups/store-$(date +%F-%H%M).sql"
```

Храните копии вне VPS и регулярно проверяйте восстановление. Сам `.env` резервируйте отдельно в зашифрованном хранилище.

### 9. Полезные команды

```bash
docker compose ps
docker compose logs -f bot
docker compose logs -f backend
docker compose restart bot backend
docker compose exec postgres psql -U store_manager -d store_manager
docker compose run --rm migrate
```

### 10. Безопасность перед production

- отключите SSH-вход root и парольную авторизацию;
- используйте SSH-ключ и fail2ban;
- перевыпускайте любой токен, который попал в чат, лог или скриншот;
- сделайте Telegram `init_data` обязательным для создания заказа;
- добавьте rate limiting для API;
- настройте CSP, HSTS и остальные защитные HTTP-заголовки;
- запускайте контейнеры от непривилегированных пользователей;
- закрепите версии зависимостей и базовых образов;
- настройте автоматические дампы PostgreSQL и мониторинг.

Подробный контекст для следующего разработчика или AI находится в [`docs/README_AI_HANDOFF.md`](docs/README_AI_HANDOFF.md).

---

## English

Vape bazar Store Manager is a Telegram commerce system combining a customer bot, an admin workflow, a product channel and a mobile Mini App.

### Features

- product catalog in the Telegram bot and Mini App;
- vape-specific product categories;
- guided admin product creation;
- stock quantity, condition, price, discounts, description and up to five photos;
- publishing to the bot, the product channel or both;
- product archive and stock restoration;
- search, sorting, favorites and cart;
- Telegram Mini App checkout;
- order actions for keeping or completing an order;
- PostgreSQL, Redis, FastAPI, aiogram, React, Caddy and Docker Compose;
- automatic HTTPS certificates through Caddy.

### Architecture

| Component | Responsibility |
| --- | --- |
| `bot` | aiogram Telegram bot and admin workflows |
| `backend` | FastAPI catalog, media, Telegram WebApp and order API |
| `web` | React Mini App and Caddy reverse proxy |
| `postgres` | products, users, orders and audit records |
| `redis` | Telegram bot state storage |
| `migrate` | Alembic migrations applied before startup |

### Requirements

- Ubuntu 22.04 or newer;
- a domain with an A record pointing to the VPS;
- TCP ports `80` and `443` available;
- SSH key access;
- a Telegram bot created with `@BotFather`;
- a product channel and optionally a separate order channel.

At least 1 GB RAM, 1 vCPU and 10 GB storage are recommended.

### Installation

1. Create the bot and Telegram channels. Grant the bot permission to publish and edit channel messages.
2. Install Docker and Docker Compose on the VPS. Review remote installation scripts before executing them.
3. Clone the repository:

```bash
sudo install -d -m 755 /opt/vape-bazar-store
sudo chown "$USER":"$USER" /opt/vape-bazar-store
git clone https://github.com/YOUR_USERNAME/vape-bazar-store.git /opt/vape-bazar-store
cd /opt/vape-bazar-store
```

4. Configure secrets:

```bash
cp .env.production.example .env
chmod 600 .env
openssl rand -hex 32
nano .env
```

Fill every variable documented in the Russian configuration example above. Never commit `.env`, tokens, passwords, private SSH keys or database dumps.

5. Point the domain to the VPS and allow only SSH, HTTP and HTTPS through the firewall.
6. Start the stack:

```bash
docker compose config
docker compose build --pull
docker compose up -d
docker compose ps
curl -fsS https://your-domain.example/api/health
```

7. Configure the BotFather Menu Button to open `https://your-domain.example/app`.

### Updating

```bash
cd /opt/vape-bazar-store
git pull --ff-only
docker compose build --pull
docker compose up -d
docker compose ps
```

Create and verify a PostgreSQL backup before every update. Store backups outside the VPS.

### Production security checklist

- disable root and password-based SSH login;
- enable fail2ban and automatic security updates;
- rotate every exposed Telegram token;
- require verified Telegram `init_data` for all orders;
- add API rate limiting and request-size limits;
- add CSP, HSTS and other browser security headers;
- run application containers as non-root users;
- pin dependencies and base image versions;
- automate PostgreSQL backups and monitoring.

See [`docs/README_AI_HANDOFF.md`](docs/README_AI_HANDOFF.md) for the full bilingual engineering handoff.
