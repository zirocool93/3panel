from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppSettings(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(64))
    telegram_bot_token_encrypted: Mapped[str | None] = mapped_column(Text)
    telegram_admin_id: Mapped[str | None] = mapped_column(String(32))
    socks5_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    socks5_host: Mapped[str | None] = mapped_column(String(255))
    socks5_port: Mapped[int | None] = mapped_column(Integer)
    socks5_username_encrypted: Mapped[str | None] = mapped_column(Text)
    socks5_password_encrypted: Mapped[str | None] = mapped_column(Text)
    manual_payments_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    manual_payment_instructions: Mapped[str | None] = mapped_column(Text)
    telegram_stars_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telegram_stars_rate_rub: Mapped[int | None] = mapped_column(Integer)
    telegram_stars_invoice_title: Mapped[str | None] = mapped_column(String(255))
    telegram_stars_invoice_description: Mapped[str | None] = mapped_column(Text)
    cardlink_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cardlink_api_base_url: Mapped[str | None] = mapped_column(String(255))
    cardlink_shop_id: Mapped[str | None] = mapped_column(String(128))
    cardlink_api_token_encrypted: Mapped[str | None] = mapped_column(Text)
    cardlink_currency: Mapped[str | None] = mapped_column(String(3))
    cardlink_locale: Mapped[str | None] = mapped_column(String(8))
    cardlink_payer_pays_commission: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    cardlink_success_url: Mapped[str | None] = mapped_column(Text)
    cardlink_fail_url: Mapped[str | None] = mapped_column(Text)
    yookassa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    yookassa_shop_id: Mapped[str | None] = mapped_column(String(128))
    yookassa_secret_key_encrypted: Mapped[str | None] = mapped_column(Text)
    yookassa_return_url: Mapped[str | None] = mapped_column(Text)
    yookassa_currency: Mapped[str | None] = mapped_column(String(3))
