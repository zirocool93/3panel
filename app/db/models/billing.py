from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AuditActorType,
    AuditEntityType,
    OrderStatus,
    PaymentEventType,
    PaymentProviderType,
    PaymentStatus,
)
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.admin import AdminUser
    from app.db.models.subscription import VpnSubscription
    from app.db.models.tariff import Tariff
    from app.db.models.user import User


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", native_enum=False),
        default=OrderStatus.PENDING_PAYMENT,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(16))
    payment_method: Mapped[PaymentProviderType] = mapped_column(
        Enum(PaymentProviderType, name="payment_provider_type", native_enum=False)
    )
    duration_days: Mapped[int] = mapped_column()
    traffic_limit_bytes: Mapped[int | None] = mapped_column(BigInteger)
    device_limit: Mapped[int | None] = mapped_column()
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
    tariff: Mapped["Tariff"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "uq_payments_provider_external_payment_id_not_empty",
            "provider",
            "external_payment_id",
            unique=True,
            postgresql_where=text("external_payment_id IS NOT NULL AND external_payment_id != ''"),
            sqlite_where=text("external_payment_id IS NOT NULL AND external_payment_id != ''"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[PaymentProviderType] = mapped_column(
        Enum(PaymentProviderType, name="payment_provider_type", native_enum=False), index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False),
        default=PaymentStatus.CREATED,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(16))
    external_payment_id: Mapped[str | None] = mapped_column(String(255), index=True)
    invoice_payload: Mapped[str | None] = mapped_column(String(500), index=True)
    provider_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped[Order] = relationship(back_populates="payments")
    user: Mapped["User"] = relationship()
    events: Mapped[list["PaymentEvent"]] = relationship(back_populates="payment")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    provider: Mapped[PaymentProviderType] = mapped_column(
        Enum(PaymentProviderType, name="payment_provider_type", native_enum=False), index=True
    )
    event_type: Mapped[PaymentEventType] = mapped_column(
        Enum(PaymentEventType, name="payment_event_type", native_enum=False)
    )
    external_event_id: Mapped[str | None] = mapped_column(String(255), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    payment: Mapped[Payment] = relationship(back_populates="events")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(AuditActorType, name="audit_actor_type", native_enum=False), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[AuditEntityType] = mapped_column(
        Enum(AuditEntityType, name="audit_entity_type", native_enum=False), index=True
    )
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BalanceTransaction(Base, TimestampMixin):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"))
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_subscriptions.id"))
    type: Mapped[str] = mapped_column(String(64))
    payment_method: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(16), default="RUB")
    balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)

    user: Mapped["User"] = relationship(back_populates="balance_transactions")
    admin: Mapped["AdminUser | None"] = relationship()
    subscription: Mapped["VpnSubscription | None"] = relationship()
