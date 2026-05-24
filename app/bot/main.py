import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.texts import ru
from app.core.config import get_settings
from app.core.logging import configure_logging

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
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        logger.warning("telegram_bot_disabled", reason=ru.BOT_DISABLED_REASON)
        return

    bot = Bot(token=token)
    await create_dispatcher().start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
