from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.crypto import encrypt_secret
from app.core.enums import AdminRole
from app.core.security import hash_password, verify_password
from app.db.models.admin import AdminUser
from app.schemas.system import (
    AdminUpdateStatus,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
    TelegramTestMessageResult,
)
from app.services.app_settings import get_or_create_app_settings, get_telegram_runtime_settings
from app.services.system.updates import (
    AdminUpdateBusy,
    AdminUpdateDisabled,
    AdminUpdateError,
    admin_update_manager,
)
from app.services.telegram import (
    TelegramTestMessageConfigurationError,
    TelegramTestMessageDeliveryError,
    send_telegram_test_message,
)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/updates", response_model=AdminUpdateStatus)
async def get_update_status(
    admin: AdminUser = Depends(get_current_admin),
    settings: Settings = Depends(settings_dep),
) -> AdminUpdateStatus:
    _require_owner(admin)
    return AdminUpdateStatus.model_validate(admin_update_manager.status(settings).__dict__)


@router.post(
    "/updates",
    response_model=AdminUpdateStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_update(
    admin: AdminUser = Depends(get_current_admin),
    settings: Settings = Depends(settings_dep),
) -> AdminUpdateStatus:
    _require_owner(admin)
    try:
        update_state = admin_update_manager.start(settings)
    except AdminUpdateDisabled as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AdminUpdateBusy as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AdminUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return AdminUpdateStatus.model_validate(update_state.__dict__)


@router.get("/telegram-settings", response_model=TelegramSettingsRead)
async def get_telegram_settings(
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> TelegramSettingsRead:
    _require_owner(admin)
    app_settings = await get_or_create_app_settings(session)
    await session.commit()
    return TelegramSettingsRead(
        bot_username=app_settings.telegram_bot_username,
        bot_token_set=bool(
            app_settings.telegram_bot_token_encrypted
            or settings.telegram_bot_token.get_secret_value()
        ),
        admin_telegram_id=app_settings.telegram_admin_id,
        socks5_enabled=app_settings.socks5_enabled,
        socks5_host=app_settings.socks5_host,
        socks5_port=app_settings.socks5_port,
        socks5_username_set=bool(app_settings.socks5_username_encrypted),
        admin_email=admin.email,
    )


@router.post("/telegram-settings/test-message", response_model=TelegramTestMessageResult)
async def send_telegram_settings_test_message(
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> TelegramTestMessageResult:
    _require_owner(admin)
    runtime_settings = await get_telegram_runtime_settings(session, settings)
    try:
        await send_telegram_test_message(runtime_settings)
    except TelegramTestMessageConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except TelegramTestMessageDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return TelegramTestMessageResult(
        ok=True,
        message="Тестовое сообщение отправлено администратору.",
    )


@router.put("/telegram-settings", response_model=TelegramSettingsRead)
async def update_telegram_settings(
    payload: TelegramSettingsUpdate,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> TelegramSettingsRead:
    _require_owner(admin)
    app_settings = await get_or_create_app_settings(session)

    if payload.socks5_enabled and (not payload.socks5_host or payload.socks5_port is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для Socks5 укажите хост и порт.",
        )

    is_admin_change = bool(payload.admin_email and payload.admin_email != admin.email) or bool(
        payload.new_password
    )
    if is_admin_change:
        if not payload.current_password or not verify_password(
            payload.current_password, admin.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для изменения данных администратора укажите текущий пароль.",
            )

        if payload.admin_email and payload.admin_email != admin.email:
            result = await session.execute(
                select(AdminUser).where(AdminUser.email == payload.admin_email.lower())
            )
            existing = result.scalar_one_or_none()
            if existing and existing.id != admin.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Администратор с таким email уже существует.",
                )
            admin.email = payload.admin_email.lower()
        if payload.new_password:
            admin.password_hash = hash_password(payload.new_password)

    app_settings.telegram_bot_username = payload.bot_username
    app_settings.telegram_admin_id = payload.admin_telegram_id
    app_settings.socks5_enabled = payload.socks5_enabled
    app_settings.socks5_host = payload.socks5_host if payload.socks5_enabled else None
    app_settings.socks5_port = payload.socks5_port if payload.socks5_enabled else None

    if payload.bot_token is not None:
        app_settings.telegram_bot_token_encrypted = encrypt_secret(
            payload.bot_token, settings=settings
        )
    if payload.socks5_username is not None:
        app_settings.socks5_username_encrypted = encrypt_secret(
            payload.socks5_username, settings=settings
        )
    if payload.socks5_password is not None:
        app_settings.socks5_password_encrypted = encrypt_secret(
            payload.socks5_password, settings=settings
        )
    if not payload.socks5_enabled:
        app_settings.socks5_username_encrypted = None
        app_settings.socks5_password_encrypted = None

    await session.commit()
    return TelegramSettingsRead(
        bot_username=app_settings.telegram_bot_username,
        bot_token_set=bool(
            app_settings.telegram_bot_token_encrypted
            or settings.telegram_bot_token.get_secret_value()
        ),
        admin_telegram_id=app_settings.telegram_admin_id,
        socks5_enabled=app_settings.socks5_enabled,
        socks5_host=app_settings.socks5_host,
        socks5_port=app_settings.socks5_port,
        socks5_username_set=bool(app_settings.socks5_username_encrypted),
        admin_email=admin.email,
    )


def _require_owner(admin: AdminUser) -> None:
    if admin.role != AdminRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Запуск обновления доступен только владельцу.",
        )
