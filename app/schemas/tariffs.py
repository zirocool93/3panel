from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import PaymentProviderType


class TariffInboundLinkCreate(BaseModel):
    server_id: int
    inbound_id: str = Field(min_length=1, max_length=128)
    inbound_remark: str | None = Field(default=None, max_length=255)
    protocol: str | None = Field(default=None, max_length=64)


class TariffInboundLinkRead(TariffInboundLinkCreate):
    id: int

    model_config = {"from_attributes": True}


class TariffPriceCreate(BaseModel):
    payment_method: PaymentProviderType
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=16)
    enabled: bool = True


class TariffPriceRead(BaseModel):
    id: int
    payment_method: str
    amount: Decimal
    currency: str
    enabled: bool

    model_config = {"from_attributes": True}


class TariffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    duration_days: int = Field(gt=0)
    traffic_limit_gb: int | None = Field(default=None, gt=0)
    device_limit: int | None = Field(default=None, gt=0)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    is_trial: bool = False
    enabled: bool = True
    is_visible: bool = True
    sort_order: int = 0
    inbound_links: list[TariffInboundLinkCreate] = Field(default_factory=list)
    prices: list[TariffPriceCreate] = Field(default_factory=list)


class TariffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    traffic_limit_gb: int | None = Field(default=None, gt=0)
    device_limit: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_trial: bool | None = None
    enabled: bool | None = None
    is_visible: bool | None = None
    sort_order: int | None = None
    inbound_links: list[TariffInboundLinkCreate] | None = None
    prices: list[TariffPriceCreate] | None = None


class TariffRead(BaseModel):
    id: int
    name: str
    description: str | None
    duration_days: int
    traffic_limit_gb: int | None
    device_limit: int | None
    price: Decimal
    currency: str
    is_trial: bool
    enabled: bool
    is_visible: bool
    sort_order: int
    inbound_links: list[TariffInboundLinkRead]
    prices: list[TariffPriceRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
