import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer("VPNBotX is running. Purchase flows will be added in Stage 3.")

    return dispatcher


async def run_polling() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        logger.warning("telegram_bot_disabled", reason="TELEGRAM_BOT_TOKEN is empty")
        return

    bot = Bot(token=token)
    await create_dispatcher().start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
