from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import SubscriptionNodeStatus, SubscriptionStatus
from app.db.base import Base, TimestampMixin


class VpnSubscription(Base, TimestampMixin):
    __tablename__ = "vpn_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tariff_id: Mapped[int | None] = mapped_column(ForeignKey("tariffs.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", native_enum=False),
        default=SubscriptionStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    traffic_limit_bytes: Mapped[int | None] = mapped_column(BigInteger)
    traffic_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    subscription_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    is_multi_server: Mapped[bool] = mapped_column(default=False)
    payment_method: Mapped[str | None] = mapped_column(String(64))
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    duration_days: Mapped[int | None] = mapped_column(Integer)
    device_limit: Mapped[int | None] = mapped_column(Integer)
    admin_comment: Mapped[str | None] = mapped_column(String(500))

    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("Tariff", back_populates="subscriptions")
    nodes: Mapped[list["VpnSubscriptionNode"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class VpnSubscriptionNode(Base, TimestampMixin):
    __tablename__ = "vpn_subscription_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("vpn_subscriptions.id", ondelete="CASCADE")
    )
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    inbound_id: Mapped[str] = mapped_column(String(128))
    protocol: Mapped[str] = mapped_column(String(64))
    client_uuid: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255))
    sub_id: Mapped[str | None] = mapped_column(String(255))
    xui_client_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[SubscriptionNodeStatus] = mapped_column(
        Enum(SubscriptionNodeStatus, name="subscription_node_status", native_enum=False),
        default=SubscriptionNodeStatus.PENDING,
    )
    traffic_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    subscription: Mapped[VpnSubscription] = relationship(back_populates="nodes")
    server = relationship("Server", back_populates="subscription_nodes")
