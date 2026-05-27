from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from app.services.app_settings import TelegramRuntimeSettings


class TelegramTestMessageConfigurationError(ValueError):
    pass


class TelegramTestMessageDeliveryError(RuntimeError):
    pass


async def send_telegram_test_message(runtime_settings: TelegramRuntimeSettings) -> None:
    if not runtime_settings.bot_token:
        raise TelegramTestMessageConfigurationError("Укажите token Telegram бота.")
    if not runtime_settings.admin_id:
        raise TelegramTestMessageConfigurationError("Укажите Telegram ID администратора.")

    proxy_session = (
        AiohttpSession(proxy=runtime_settings.socks5_proxy_url)
        if runtime_settings.socks5_proxy_url
        else None
    )
    bot: Bot | None = None
    try:
        bot = Bot(token=runtime_settings.bot_token, session=proxy_session)
        await bot.send_message(
            chat_id=runtime_settings.admin_id,
            text=(
                "Проверка VPNBotX: бот доступен и может отправлять сообщения "
                "администратору."
            ),
        )
    except TelegramTestMessageConfigurationError:
        raise
    except Exception as exc:
        raise TelegramTestMessageDeliveryError(
            "Не удалось отправить тестовое сообщение в Telegram."
        ) from exc
    finally:
        if bot is not None:
            await bot.session.close()
