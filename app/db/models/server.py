from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PanelProviderType, ServerHealthStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.subscription import VpnSubscriptionNode


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    provider_type: Mapped[PanelProviderType] = mapped_column(
        Enum(PanelProviderType, name="panel_provider_type", native_enum=False),
        default=PanelProviderType.XUI,
    )
    country: Mapped[str] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(255))
    panel_url: Mapped[str] = mapped_column(Text)
    username_encrypted: Mapped[str | None] = mapped_column(Text)
    password_encrypted: Mapped[str | None] = mapped_column(Text)
    api_token_encrypted: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[int | None] = mapped_column(Integer)
    current_users: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    subscription_base_url: Mapped[str | None] = mapped_column(Text)
    last_health_status: Mapped[ServerHealthStatus] = mapped_column(
        Enum(ServerHealthStatus, name="server_health_status", native_enum=False),
        default=ServerHealthStatus.UNKNOWN,
    )
    last_health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group_links: Mapped[list["ServerGroupServer"]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    subscription_nodes: Mapped[list["VpnSubscriptionNode"]] = relationship(back_populates="server")


class ServerGroup(Base, TimestampMixin):
    __tablename__ = "server_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    server_links: Mapped[list["ServerGroupServer"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class ServerGroupServer(Base):
    __tablename__ = "server_group_servers"
    __table_args__ = (UniqueConstraint("group_id", "server_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("server_groups.id", ondelete="CASCADE"))
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[ServerGroup] = relationship(back_populates="server_links")
    server: Mapped[Server] = relationship(back_populates="group_links")
