import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.router import build_router
from app.bot.texts import ru
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory
from app.services.app_settings import get_telegram_runtime_settings

logger = structlog.get_logger(__name__)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router())
    return dispatcher


async def run_polling() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    async with async_session_factory() as db_session:
        telegram_settings = await get_telegram_runtime_settings(db_session, settings)

    if not telegram_settings.bot_token:
        logger.warning("telegram_bot_disabled", reason=ru.BOT_DISABLED_REASON)
        return

    aiohttp_session = (
        AiohttpSession(proxy=telegram_settings.socks5_proxy_url)
        if telegram_settings.socks5_proxy_url
        else None
    )
    bot = Bot(
        token=telegram_settings.bot_token,
        session=aiohttp_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await create_dispatcher().start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
