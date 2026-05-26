from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.core.enums import PanelProviderType, ServerHealthStatus


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=128)
    location: str | None = None
    panel_url: HttpUrl
    username: str | None = None
    password: str | None = None
    api_token: str | None = None
    enabled: bool = True
    max_users: int | None = Field(default=None, ge=1)
    priority: int = Field(default=100, ge=0)
    subscription_base_url: HttpUrl | None = None


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=1, max_length=128)
    location: str | None = None
    panel_url: HttpUrl | None = None
    username: str | None = None
    password: str | None = None
    api_token: str | None = None
    enabled: bool | None = None
    max_users: int | None = Field(default=None, ge=1)
    priority: int | None = Field(default=None, ge=0)
    subscription_base_url: HttpUrl | None = None


class ServerRead(BaseModel):
    id: int
    name: str
    provider_type: PanelProviderType
    country: str
    location: str | None
    panel_url: str
    enabled: bool
    max_users: int | None
    current_users: int
    priority: int
    subscription_base_url: str | None
    last_health_status: ServerHealthStatus
    last_health_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerHealthRead(BaseModel):
    ok: bool
    status: ServerHealthStatus
    message: str


class ServerInboundRead(BaseModel):
    id: int
    remark: str | None = None
    protocol: str | None = None
    enable: bool | None = None
    port: int | None = None


class XuiClientRead(BaseModel):
    inbound_id: int
    inbound_remark: str | None = None
    protocol: str | None = None
    email: str
    client_uuid: str | None = None
    sub_id: str | None = None
    enable: bool | None = None
    expiry_time: int | None = None
    traffic_limit: int = 0
    up: int = 0
    down: int = 0
    total: int = 0
