# Architecture

## Modules

```text
api / bot / cli / workers
        |
application services
        |
repositories and provider interfaces
        |
PostgreSQL / Redis / 3X-UI / payment APIs
```

The API, bot and worker entrypoints must stay thin. Commercial rules live in services, persistence
in repositories and external panel or payment behavior behind provider interfaces.

## Stage 1 tables

The first migration creates:

- `users`;
- `admin_users`;
- `admin_refresh_tokens`;
- `servers`;
- `server_groups`;
- `server_group_servers`;
- `tariffs`;
- `tariff_groups`;
- `tariff_group_tariffs`;
- `tariff_server_groups`;
- `vpn_subscriptions`;
- `vpn_subscription_nodes`.

Later migrations add orders, payments, balance ledger, promocodes, promo links, referral rewards,
broadcasts, notifications, audit logs and settings.

## Order lifecycle target

```text
draft -> pending_payment -> paid -> fulfilled
                     \-> expired | cancelled
```

Payments remain separate from orders. Provider events are idempotent and order pricing is frozen
when the order is created.

## Subscription lifecycle target

```text
pending -> active -> expired
        \-> provisioning_failed
active  -> disabled
```

`vpn_subscriptions` is the commercial parent. `vpn_subscription_nodes` tracks clients created on
specific VPN panel servers, which allows one parent subscription to expose multiple server configs.

## Panel integration

`PanelProvider` defines the panel contract. `XuiProvider` is the first implementation area. Marzban
or Hiddify adapters should implement the same service boundary rather than leak panel-specific
payloads into order and subscription logic.

