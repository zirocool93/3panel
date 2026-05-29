from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.bot import keyboards
from app.bot.texts import ru
from app.core.config import get_settings
from app.db.models.user import User
from app.db.session import async_session_factory
from app.services.app_settings import get_telegram_runtime_settings
from app.services.bot_facades import BotUserFacade

router = Router(name="menu")


@router.message(Command("menu"))
async def menu_command(message: Message) -> None:
    await message.answer(ru.MAIN_MENU, reply_markup=keyboards.main_menu())


@router.callback_query(F.data == "menu:main")
async def menu_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(ru.MAIN_MENU, reply_markup=keyboards.main_menu())
    await callback.answer()


async def show_main_menu(message: Message) -> None:
    await message.answer(ru.MAIN_MENU, reply_markup=keyboards.main_menu())


@router.callback_query(F.data == "guides:list")
async def guides_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(ru.GUIDE_INTRO, reply_markup=keyboards.guides_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("guide:"))
async def guide_callback(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1] if callback.data else ""
    text = ru.GUIDES.get(key, ru.GUIDE_INTRO)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboards.guides_menu())
    await callback.answer()


@router.message(Command("terms"))
async def terms_command(message: Message) -> None:
    await message.answer(ru.TERMS, reply_markup=keyboards.back_menu())


@router.message(Command("privacy"))
async def privacy_command(message: Message) -> None:
    await message.answer(ru.PRIVACY, reply_markup=keyboards.back_menu())


@router.message(Command("ref"))
async def ref_command(message: Message) -> None:
    await _send_referral(message)


@router.callback_query(F.data == "ref:show")
async def ref_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await _send_referral(callback.message, telegram_id=callback.from_user.id)
    await callback.answer()


@router.message(Command("promo"))
async def promo_command(message: Message) -> None:
    await message.answer(ru.PROMO_TODO, reply_markup=keyboards.back_menu())


@router.callback_query(F.data == "promo:show")
async def promo_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(ru.PROMO_TODO, reply_markup=keyboards.back_menu())
    await callback.answer()


async def _send_referral(message: Message, telegram_id: int | None = None) -> None:
    effective_telegram_id = telegram_id or (message.from_user.id if message.from_user else None)
    if effective_telegram_id is None:
        return
    async with async_session_factory() as session:
        user = await BotUserFacade(session).get_user_by_telegram_id(effective_telegram_id)
        if not user:
            await message.answer("Сначала отправьте /start.")
            return
        runtime_settings = await get_telegram_runtime_settings(session, get_settings())
        bot_username = runtime_settings.bot_username
        invited_count = await session.scalar(
            select(func.count(User.id)).where(User.referrer_id == user.id)
        )
    if not bot_username:
        await message.answer("Bot username не настроен.", reply_markup=keyboards.back_menu())
        return
    link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    await message.answer(
        f"Ваша реферальная ссылка:\n{link}\n\nПриглашённых: {int(invited_count or 0)}",
        reply_markup=keyboards.back_menu(),
    )
