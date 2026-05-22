from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ServerGroupSelectionMode
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.subscription import VpnSubscription


class Tariff(Base, TimestampMixin):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    duration_days: Mapped[int] = mapped_column(Integer)
    traffic_limit_gb: Mapped[int | None] = mapped_column(Integer)
    device_limit: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    subscriptions: Mapped[list["VpnSubscription"]] = relationship(back_populates="tariff")
    server_group_links: Mapped[list["TariffServerGroup"]] = relationship(
        back_populates="tariff", cascade="all, delete-orphan"
    )


class TariffGroup(Base, TimestampMixin):
    __tablename__ = "tariff_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    tariff_links: Mapped[list["TariffGroupTariff"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class TariffGroupTariff(Base):
    __tablename__ = "tariff_group_tariffs"
    __table_args__ = (UniqueConstraint("group_id", "tariff_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("tariff_groups.id", ondelete="CASCADE"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id", ondelete="CASCADE"))

    group: Mapped[TariffGroup] = relationship(back_populates="tariff_links")


class TariffServerGroup(Base):
    __tablename__ = "tariff_server_groups"
    __table_args__ = (UniqueConstraint("tariff_id", "server_group_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id", ondelete="CASCADE"))
    server_group_id: Mapped[int] = mapped_column(ForeignKey("server_groups.id", ondelete="CASCADE"))
    selection_mode: Mapped[ServerGroupSelectionMode] = mapped_column(
        Enum(ServerGroupSelectionMode, name="server_group_selection_mode", native_enum=False),
        default=ServerGroupSelectionMode.ALL,
    )

    tariff: Mapped[Tariff] = relationship(back_populates="server_group_links")
