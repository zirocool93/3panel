from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import decrypt_secret
from app.db.models.app_settings import AppSettings

SETTINGS_ROW_ID = 1


@dataclass(frozen=True)
class TelegramRuntimeSettings:
    bot_token: str
    bot_username: str | None
    admin_id: str | None
    socks5_proxy_url: str | None


async def get_or_create_app_settings(session: AsyncSession) -> AppSettings:
    app_settings = await session.get(AppSettings, SETTINGS_ROW_ID)
    if app_settings:
        return app_settings

    app_settings = AppSettings(id=SETTINGS_ROW_ID)
    session.add(app_settings)
    await session.flush()
    return app_settings


async def get_telegram_runtime_settings(
    session: AsyncSession, settings: Settings
) -> TelegramRuntimeSettings:
    app_settings = await get_or_create_app_settings(session)
    bot_token = decrypt_secret(app_settings.telegram_bot_token_encrypted, settings=settings)
    if not bot_token:
        bot_token = settings.telegram_bot_token.get_secret_value()

    return TelegramRuntimeSettings(
        bot_token=bot_token,
        bot_username=app_settings.telegram_bot_username,
        admin_id=app_settings.telegram_admin_id,
        socks5_proxy_url=_build_socks5_proxy_url(app_settings, settings),
    )


def _build_socks5_proxy_url(app_settings: AppSettings, settings: Settings) -> str | None:
    if not app_settings.socks5_enabled:
        return None
    if not app_settings.socks5_host or not app_settings.socks5_port:
        return None

    username = decrypt_secret(app_settings.socks5_username_encrypted, settings=settings)
    password = decrypt_secret(app_settings.socks5_password_encrypted, settings=settings)
    credentials = ""
    if username:
        credentials = quote(username, safe="")
        if password:
            credentials = f"{credentials}:{quote(password, safe='')}"
        credentials = f"{credentials}@"
    return f"socks5://{credentials}{app_settings.socks5_host}:{app_settings.socks5_port}"
