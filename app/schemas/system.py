from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminUpdateStatus(BaseModel):
    enabled: bool
    running: bool
    ref: str
    log_tail: list[str]


class TelegramSettingsRead(BaseModel):
    bot_username: str | None
    bot_token_set: bool
    admin_telegram_id: str | None
    socks5_enabled: bool
    socks5_host: str | None
    socks5_port: int | None
    socks5_username_set: bool
    admin_email: EmailStr


class TelegramTestMessageResult(BaseModel):
    ok: bool
    message: str


class TelegramSettingsUpdate(BaseModel):
    bot_username: str | None = Field(default=None, max_length=64)
    bot_token: str | None = Field(default=None, max_length=256)
    admin_telegram_id: str | None = Field(default=None, max_length=32)
    socks5_enabled: bool = False
    socks5_host: str | None = Field(default=None, max_length=255)
    socks5_port: int | None = Field(default=None, ge=1, le=65535)
    socks5_username: str | None = Field(default=None, max_length=255)
    socks5_password: str | None = Field(default=None, max_length=255)
    admin_email: EmailStr | None = None
    current_password: str | None = Field(default=None, min_length=8, max_length=256)
    new_password: str | None = Field(default=None, min_length=8, max_length=256)

    @field_validator(
        "bot_username",
        "bot_token",
        "admin_telegram_id",
        "socks5_host",
        "socks5_username",
        "socks5_password",
        "current_password",
        "new_password",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
