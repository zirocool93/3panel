from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.billing import BalanceTransaction
    from app.db.models.subscription import VpnSubscription


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    comment: Mapped[str | None] = mapped_column(Text)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    start_payload: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(255), index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    referrer: Mapped["User | None"] = relationship(remote_side="User.id")
    subscriptions: Mapped[list["VpnSubscription"]] = relationship(back_populates="user")
    balance_transactions: Mapped[list["BalanceTransaction"]] = relationship(back_populates="user")
