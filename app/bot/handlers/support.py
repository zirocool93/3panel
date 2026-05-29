import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.admin_notify import notify_admin
from app.bot.states import SupportStates
from app.bot.texts import ru
from app.db.session import async_session_factory

router = Router(name="support")
logger = structlog.get_logger(__name__)

SUPPORT_CATEGORIES = {
    "connect": "Не подключается",
    "speed": "Низкая скорость",
    "pay": "Оплатил, но доступ не пришёл",
    "guide": "Нужна инструкция",
    "other": "Другое",
    "payments": "Платежи",
}


@router.message(Command("support"))
async def support_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Выберите категорию обращения:",
        reply_markup=keyboards.support_categories(),
    )


@router.message(Command("paysupport"))
async def pay_support_command(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_message)
    await state.update_data(category="Платежи")
    await message.answer(ru.PAY_SUPPORT, reply_markup=keyboards.back_menu())


@router.callback_query(F.data == "support:start")
async def support_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Выберите категорию обращения:",
            reply_markup=keyboards.support_categories(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("support:cat:"))
async def support_category(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.rsplit(":", 1)[-1] if callback.data else "other"
    category = SUPPORT_CATEGORIES.get(code, SUPPORT_CATEGORIES["other"])
    await state.set_state(SupportStates.waiting_message)
    await state.update_data(category=category)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"Категория: {category}\n\nОпишите проблему одним сообщением.",
            reply_markup=keyboards.back_menu(),
        )
    await callback.answer()


@router.message(SupportStates.waiting_message)
async def support_message(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    category = str(data.get("category") or "Другое")
    text = message.text or message.caption or ""
    await state.clear()
    username = (
        message.from_user.username if message.from_user and message.from_user.username else "-"
    )
    admin_message = (
        "Новая заявка в поддержку\n\n"
        f"Категория: {category}\n"
        f"Telegram ID: {message.from_user.id if message.from_user else 'unknown'}\n"
        f"Username: @{username}\n"
        f"Сообщение:\n{text}"
    )
    async with async_session_factory() as session:
        delivered = await notify_admin(bot, session, admin_message)
        await session.commit()
    # TODO: persist SupportTicket when the ticket model is introduced.
    if delivered:
        await message.answer(ru.SUPPORT_ACCEPTED, reply_markup=keyboards.main_menu())
    else:
        await message.answer(ru.SUPPORT_ADMIN_NOT_CONFIGURED, reply_markup=keyboards.main_menu())
