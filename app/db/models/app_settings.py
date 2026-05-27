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
