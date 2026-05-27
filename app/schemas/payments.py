from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.core.enums import PaymentProviderType


class PaymentMethodRead(BaseModel):
    code: PaymentProviderType
    label: str
    enabled: bool


class PaymentSettingsRead(BaseModel):
    manual_payments_enabled: bool
    manual_payment_instructions: str | None
    telegram_stars_enabled: bool
    telegram_stars_rate_rub: int | None
    telegram_stars_invoice_title: str | None
    telegram_stars_invoice_description: str | None
    cardlink_enabled: bool
    cardlink_api_base_url: str | None
    cardlink_shop_id: str | None
    cardlink_api_token_set: bool
    cardlink_currency: str | None
    cardlink_locale: str | None
    cardlink_payer_pays_commission: bool
    cardlink_success_url: str | None
    cardlink_fail_url: str | None
    yookassa_enabled: bool
    yookassa_shop_id: str | None
    yookassa_secret_key_set: bool
    yookassa_return_url: str | None
    yookassa_currency: str | None


class PaymentSettingsUpdate(BaseModel):
    manual_payments_enabled: bool = True
    manual_payment_instructions: str | None = Field(default=None, max_length=5000)
    telegram_stars_enabled: bool = False
    telegram_stars_rate_rub: int | None = Field(default=None, ge=1, le=100000)
    telegram_stars_invoice_title: str | None = Field(default=None, max_length=255)
    telegram_stars_invoice_description: str | None = Field(default=None, max_length=2000)
    cardlink_enabled: bool = False
    cardlink_api_base_url: HttpUrl | None = None
    cardlink_shop_id: str | None = Field(default=None, max_length=128)
    cardlink_api_token: str | None = Field(default=None, max_length=512)
    cardlink_currency: str | None = Field(default="RUB", min_length=3, max_length=3)
    cardlink_locale: str | None = Field(default="ru", max_length=8)
    cardlink_payer_pays_commission: bool = True
    cardlink_success_url: HttpUrl | None = None
    cardlink_fail_url: HttpUrl | None = None
    yookassa_enabled: bool = False
    yookassa_shop_id: str | None = Field(default=None, max_length=128)
    yookassa_secret_key: str | None = Field(default=None, max_length=512)
    yookassa_return_url: HttpUrl | None = None
    yookassa_currency: str | None = Field(default="RUB", min_length=3, max_length=3)

    @field_validator(
        "manual_payment_instructions",
        "telegram_stars_invoice_title",
        "telegram_stars_invoice_description",
        "cardlink_shop_id",
        "cardlink_api_token",
        "cardlink_currency",
        "cardlink_locale",
        "yookassa_shop_id",
        "yookassa_secret_key",
        "yookassa_currency",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
