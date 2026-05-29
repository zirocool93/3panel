import structlog
from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from app.bot import keyboards
from app.bot.formatters import tariff_card
from app.bot.texts import ru
from app.core.enums import PaymentProviderType
from app.db.session import async_session_factory
from app.services.bot_facades import BotUserFacade
from app.services.users import BlockedUserError

router = Router(name="start")
logger = structlog.get_logger(__name__)


@router.message(CommandStart())
async def start_command(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        return
    payload = command.args
    async with async_session_factory() as session:
        try:
            user = await BotUserFacade(session).start_user(
                {
                    "telegram_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "language_code": message.from_user.language_code,
                    "display_name": message.from_user.full_name,
                },
                payload,
            )
            await session.commit()
        except BlockedUserError:
            await message.answer("Ваш аккаунт заблокирован.")
            return
        except Exception as exc:
            logger.warning("bot_start_failed", error=str(exc), telegram_id=message.from_user.id)
            await message.answer("Не удалось открыть меню. Попробуйте позже.")
            return

    await message.answer(ru.START, reply_markup=keyboards.main_menu())
    if payload and payload.startswith("plan_"):
        await _show_deep_link_plan(message, user.id, payload)


async def _show_deep_link_plan(message: Message, user_id: int, payload: str) -> None:
    raw_tariff_id = payload.removeprefix("plan_")
    if not raw_tariff_id.isdigit():
        return
    async with async_session_factory() as session:
        tariff = await BotUserFacade(session).get_tariff(
            int(raw_tariff_id),
            PaymentProviderType.TELEGRAM_STARS,
        )
    if not tariff:
        await message.answer(ru.TARIFF_UNAVAILABLE, reply_markup=keyboards.back_menu())
        return
    await message.answer(
        tariff_card(tariff),
        reply_markup=keyboards.catalog_actions(tariff.id),
        parse_mode="HTML",
    )
