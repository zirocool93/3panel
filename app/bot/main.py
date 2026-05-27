import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.texts import ru
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory
from app.services.app_settings import get_telegram_runtime_settings

logger = structlog.get_logger(__name__)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(ru.START)

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
    bot = Bot(token=telegram_settings.bot_token, session=aiohttp_session)
    await create_dispatcher().start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
