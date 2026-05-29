from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import OrderStatus, PaymentProviderType, PaymentStatus, SubscriptionStatus


class TariffCatalogItem(BaseModel):
    id: int
    name: str
    description: str | None
    duration_days: int
    traffic_limit_gb: int | None
    device_limit: int | None
    is_trial: bool
    price: Decimal
    currency: str
    payment_method_prices: dict[str, dict[str, Decimal | str]]
    available_payment_methods: list[str]


class OrderCreate(BaseModel):
    user_id: int
    tariff_id: int
    payment_method: PaymentProviderType
    allow_hidden_plan: bool = False


class OrderRead(BaseModel):
    id: int
    user_id: int
    tariff_id: int
    status: OrderStatus
    amount: Decimal
    currency: str
    payment_method: PaymentProviderType
    duration_days: int
    traffic_limit_bytes: int | None
    device_limit: int | None
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None
    paid_at: datetime | None
    fulfilled_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    order_id: int
    provider: PaymentProviderType


class PaymentRead(BaseModel):
    id: int
    order_id: int
    user_id: int
    provider: PaymentProviderType
    status: PaymentStatus
    amount: Decimal
    currency: str
    external_payment_id: str | None
    invoice_payload: str | None
    idempotency_key: str
    paid_at: datetime | None
    failed_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ManualReject(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class SubscriptionInfo(BaseModel):
    status: SubscriptionStatus
    tariff: str | None
    expires_at: datetime | None
    traffic_used_bytes: int
    traffic_limit_bytes: int | None
    nodes: int
    server_countries: list[str]
    is_active: bool


class DashboardSummary(BaseModel):
    users_total: int
    users_new_today: int
    orders_today: int
    payments_today: int
    revenue_today: Decimal
    revenue_month: Decimal
    active_subscriptions: int
    expiring_soon: int
    provisioning_failed: int
    manual_payments_pending: int
    servers_online: int
    servers_degraded: int
    servers_offline: int
