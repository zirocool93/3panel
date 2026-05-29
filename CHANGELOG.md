# Changelog

## 0.2.0

- Added Stage 2 commerce backend: orders, payments, payment events and audit log models.
- Added Telegram user attribution fields and `UserService`.
- Added tariff catalog, order, payment, Telegram Stars, trial, subscription and provisioning services.
- Added Celery provisioning task and admin APIs for orders, payments, subscriptions and dashboard summary.
- Added public `/sub/{token}` and `/sub/{token}/info` endpoints.
- Added critical pytest coverage for Telegram users, order snapshots, payment idempotency, provisioning and subscription endpoint access.

## 0.1.0

- Added the Stage 1 backend, bot, worker, scheduler, frontend, Docker and deployment skeleton.
