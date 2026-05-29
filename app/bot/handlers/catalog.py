import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.formatters import tariff_card
from app.bot.texts import ru
from app.core.enums import PaymentProviderType
from app.db.session import async_session_factory
from app.services.bot_facades import BotUserFacade

router = Router(name="catalog")
logger = structlog.get_logger(__name__)


@router.message(Command("buy"))
async def buy_command(message: Message) -> None:
    await show_catalog(message)


@router.callback_query(F.data == "catalog:list")
async def catalog_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await show_catalog(callback.message)
    await callback.answer()


async def show_catalog(message: Message) -> None:
    if not message.from_user:
        return
    async with async_session_factory() as session:
        user = await BotUserFacade(session).get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала отправьте /start.")
            return
        tariffs = await BotUserFacade(session).get_tariffs(
            user.id,
            PaymentProviderType.TELEGRAM_STARS,
        )
    if not tariffs:
        await message.answer(ru.NO_TARIFFS, reply_markup=keyboards.back_menu())
        return
    for tariff in tariffs:
        await message.answer(
            tariff_card(tariff),
            reply_markup=keyboards.catalog_actions(tariff.id),
            parse_mode="HTML",
        )
