from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.crypto import encrypt_secret
from app.core.enums import AdminRole, PaymentProviderType
from app.db.models.admin import AdminUser
from app.db.models.app_settings import AppSettings
from app.schemas.payments import PaymentMethodRead, PaymentSettingsRead, PaymentSettingsUpdate
from app.services.app_settings import get_or_create_app_settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/methods", response_model=list[PaymentMethodRead])
async def list_payment_methods(
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[PaymentMethodRead]:
    app_settings = await get_or_create_app_settings(session)
    await session.commit()
    return _payment_methods(app_settings)


@router.get("/settings", response_model=PaymentSettingsRead)
async def get_payment_settings(
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> PaymentSettingsRead:
    _require_owner_or_accountant(admin)
    app_settings = await get_or_create_app_settings(session)
    await session.commit()
    return _settings_read(app_settings)


@router.put("/settings", response_model=PaymentSettingsRead)
async def update_payment_settings(
    payload: PaymentSettingsUpdate,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> PaymentSettingsRead:
    _require_owner(admin)
    _validate_payment_settings(payload)
    app_settings = await get_or_create_app_settings(session)

    app_settings.manual_payments_enabled = payload.manual_payments_enabled
    app_settings.manual_payment_instructions = payload.manual_payment_instructions
    app_settings.telegram_stars_enabled = payload.telegram_stars_enabled
    app_settings.telegram_stars_rate_rub = payload.telegram_stars_rate_rub
    app_settings.telegram_stars_invoice_title = payload.telegram_stars_invoice_title
    app_settings.telegram_stars_invoice_description = payload.telegram_stars_invoice_description
    app_settings.cardlink_enabled = payload.cardlink_enabled
    app_settings.cardlink_api_base_url = (
        str(payload.cardlink_api_base_url).rstrip("/") if payload.cardlink_api_base_url else None
    )
    app_settings.cardlink_shop_id = payload.cardlink_shop_id
    app_settings.cardlink_currency = (
        payload.cardlink_currency.upper() if payload.cardlink_currency else None
    )
    app_settings.cardlink_locale = payload.cardlink_locale
    app_settings.cardlink_payer_pays_commission = payload.cardlink_payer_pays_commission
    app_settings.cardlink_success_url = (
        str(payload.cardlink_success_url) if payload.cardlink_success_url else None
    )
    app_settings.cardlink_fail_url = (
        str(payload.cardlink_fail_url) if payload.cardlink_fail_url else None
    )
    app_settings.yookassa_enabled = payload.yookassa_enabled
    app_settings.yookassa_shop_id = payload.yookassa_shop_id
    app_settings.yookassa_return_url = (
        str(payload.yookassa_return_url) if payload.yookassa_return_url else None
    )
    app_settings.yookassa_currency = (
        payload.yookassa_currency.upper() if payload.yookassa_currency else None
    )

    if payload.cardlink_api_token is not None:
        app_settings.cardlink_api_token_encrypted = encrypt_secret(
            payload.cardlink_api_token, settings=settings
        )
    if payload.yookassa_secret_key is not None:
        app_settings.yookassa_secret_key_encrypted = encrypt_secret(
            payload.yookassa_secret_key, settings=settings
        )

    await session.commit()
    return _settings_read(app_settings)


def _validate_payment_settings(payload: PaymentSettingsUpdate) -> None:
    if payload.telegram_stars_enabled and not payload.telegram_stars_rate_rub:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для Telegram Stars укажите курс: сколько Stars соответствует 1 RUB.",
        )
    if payload.cardlink_enabled and (
        not payload.cardlink_api_base_url or not payload.cardlink_shop_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для Cardlink укажите API URL и Shop ID.",
        )
    if payload.yookassa_enabled and (
        not payload.yookassa_shop_id or not payload.yookassa_return_url
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для ЮKassa укажите Shop ID и return URL.",
        )


def _payment_methods(app_settings: AppSettings) -> list[PaymentMethodRead]:
    return [
        PaymentMethodRead(
            code=PaymentProviderType.MANUAL,
            label="Ручная оплата",
            enabled=app_settings.manual_payments_enabled,
        ),
        PaymentMethodRead(
            code=PaymentProviderType.BALANCE,
            label="Баланс",
            enabled=True,
        ),
        PaymentMethodRead(
            code=PaymentProviderType.TELEGRAM_STARS,
            label="Telegram Stars",
            enabled=app_settings.telegram_stars_enabled,
        ),
        PaymentMethodRead(
            code=PaymentProviderType.CRYPTO,
            label="Крипта",
            enabled=False,
        ),
        PaymentMethodRead(
            code=PaymentProviderType.CARDLINK,
            label="Cardlink",
            enabled=app_settings.cardlink_enabled,
        ),
        PaymentMethodRead(
            code=PaymentProviderType.YOOKASSA,
            label="ЮKassa",
            enabled=app_settings.yookassa_enabled,
        ),
    ]


def _settings_read(app_settings: AppSettings) -> PaymentSettingsRead:
    return PaymentSettingsRead(
        manual_payments_enabled=app_settings.manual_payments_enabled,
        manual_payment_instructions=app_settings.manual_payment_instructions,
        telegram_stars_enabled=app_settings.telegram_stars_enabled,
        telegram_stars_rate_rub=app_settings.telegram_stars_rate_rub,
        telegram_stars_invoice_title=app_settings.telegram_stars_invoice_title,
        telegram_stars_invoice_description=app_settings.telegram_stars_invoice_description,
        cardlink_enabled=app_settings.cardlink_enabled,
        cardlink_api_base_url=app_settings.cardlink_api_base_url,
        cardlink_shop_id=app_settings.cardlink_shop_id,
        cardlink_api_token_set=bool(app_settings.cardlink_api_token_encrypted),
        cardlink_currency=app_settings.cardlink_currency,
        cardlink_locale=app_settings.cardlink_locale,
        cardlink_payer_pays_commission=app_settings.cardlink_payer_pays_commission,
        cardlink_success_url=app_settings.cardlink_success_url,
        cardlink_fail_url=app_settings.cardlink_fail_url,
        yookassa_enabled=app_settings.yookassa_enabled,
        yookassa_shop_id=app_settings.yookassa_shop_id,
        yookassa_secret_key_set=bool(app_settings.yookassa_secret_key_encrypted),
        yookassa_return_url=app_settings.yookassa_return_url,
        yookassa_currency=app_settings.yookassa_currency,
    )


def _require_owner(admin: AdminUser) -> None:
    if admin.role != AdminRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Настройки платежей может менять только владелец.",
        )


def _require_owner_or_accountant(admin: AdminUser) -> None:
    if admin.role not in {AdminRole.OWNER, AdminRole.ACCOUNTANT}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Настройки платежей доступны владельцу и бухгалтеру.",
        )
