from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.core.enums import SubscriptionStatus


class ClientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    telegram_id: int | None = None
    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    comment: str | None = None


class ClientUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    telegram_id: int | None = None
    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    comment: str | None = None
    is_blocked: bool | None = None


class ClientSubscriptionCreate(BaseModel):
    tariff_id: int
    payment_method: str = Field(min_length=1, max_length=64)
    price_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    duration_days: int | None = Field(default=None, gt=0)
    traffic_limit_gb: int | None = Field(default=None, gt=0)
    device_limit: int | None = Field(default=None, gt=0)
    admin_comment: str | None = Field(default=None, max_length=500)


class ClientSubscriptionUpdate(BaseModel):
    tariff_id: int | None = None
    status: SubscriptionStatus | None = None
    payment_method: str | None = Field(default=None, min_length=1, max_length=64)
    price_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    duration_days: int | None = Field(default=None, gt=0)
    traffic_limit_gb: int | None = Field(default=None, gt=0)
    device_limit: int | None = Field(default=None, gt=0)
    admin_comment: str | None = Field(default=None, max_length=500)


class ClientBalanceAdjust(BaseModel):
    amount: Decimal
    currency: str = Field(default="RUB", min_length=3, max_length=16)
    description: str | None = Field(default=None, max_length=1000)


class ClientTransactionRead(BaseModel):
    id: int
    user_id: int
    user_display_name: str | None = None
    admin_id: int | None
    subscription_id: int | None
    type: str
    payment_method: str | None
    amount: Decimal
    currency: str
    balance_before: Decimal
    balance_after: Decimal
    description: str | None
    external_id: str | None
    created_at: datetime


class ClientSubscriptionRead(BaseModel):
    id: int
    tariff_id: int | None
    tariff_name: str | None = None
    status: SubscriptionStatus
    payment_method: str | None
    price_amount: Decimal | None
    currency: str | None
    duration_days: int | None
    traffic_limit_gb: int | None = None
    device_limit: int | None
    started_at: datetime | None
    expires_at: datetime | None
    subscription_token: str
    subscription_url: str | None = None
    subscription_qr: str | None = None
    nodes_count: int = 0
    nodes: list["ClientSubscriptionNodeRead"] = Field(default_factory=list)
    admin_comment: str | None
    created_at: datetime


class ClientSubscriptionNodeRead(BaseModel):
    id: int
    server_id: int
    inbound_id: str
    protocol: str
    email: str | None
    client_uuid: str | None
    sub_id: str | None
    status: str
    subscription_url: str | None = None
    subscription_qr: str | None = None
    error: str | None = None


class ClientRead(BaseModel):
    id: int
    display_name: str | None
    telegram_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None
    comment: str | None
    balance: Decimal
    is_blocked: bool
    subscriptions_count: int = 0
    subscriptions: list[ClientSubscriptionRead] = Field(default_factory=list)
    transactions: list[ClientTransactionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def ensure_display_name(self) -> "ClientRead":
        if not self.display_name:
            self.display_name = " ".join(
                part for part in [self.first_name, self.last_name] if part
            ) or self.username
        return self
