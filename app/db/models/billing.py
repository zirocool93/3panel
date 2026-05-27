from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BalanceTransactionType, PaymentProviderType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.admin import AdminUser
    from app.db.models.subscription import VpnSubscription
    from app.db.models.user import User


class BalanceTransaction(Base, TimestampMixin):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"))
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_subscriptions.id"))
    type: Mapped[BalanceTransactionType] = mapped_column(
        Enum(BalanceTransactionType, name="balance_transaction_type", native_enum=False)
    )
    payment_method: Mapped[PaymentProviderType | None] = mapped_column(
        Enum(PaymentProviderType, name="payment_provider_type", native_enum=False)
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(16), default="RUB")
    balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)

    user: Mapped["User"] = relationship(back_populates="balance_transactions")
    admin: Mapped["AdminUser | None"] = relationship()
    subscription: Mapped["VpnSubscription | None"] = relationship()
