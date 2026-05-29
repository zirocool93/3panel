import structlog
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.services.app_settings import get_telegram_runtime_settings

logger = structlog.get_logger(__name__)


async def notify_admin(
    bot: Bot,
    session: AsyncSession,
    message: str,
    settings: Settings | None = None,
) -> bool:
    runtime_settings = await get_telegram_runtime_settings(session, settings or get_settings())
    if not runtime_settings.admin_id:
        logger.warning("telegram_admin_not_configured")
        return False
    try:
        await bot.send_message(chat_id=int(runtime_settings.admin_id), text=message)
    except Exception as exc:
        logger.warning("telegram_admin_notify_failed", error=str(exc))
        return False
    return True
