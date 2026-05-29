import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.admin_notify import notify_admin
from app.bot.texts import ru
from app.db.session import async_session_factory
from app.services.bot_facades import BotUserFacade
from app.services.trial import TrialError

router = Router(name="trial")
logger = structlog.get_logger(__name__)


@router.message(Command("trial"))
async def trial_command(message: Message, bot: Bot) -> None:
    await activate_trial(message, bot)


@router.callback_query(F.data == "trial:activate")
async def trial_callback(callback: CallbackQuery, bot: Bot) -> None:
    if isinstance(callback.message, Message):
        await activate_trial(callback.message, bot, telegram_id=callback.from_user.id)
    await callback.answer()


async def activate_trial(message: Message, bot: Bot, telegram_id: int | None = None) -> None:
    effective_telegram_id = telegram_id or (message.from_user.id if message.from_user else None)
    if effective_telegram_id is None:
        return
    async with async_session_factory() as session:
        try:
            user = await BotUserFacade(session).get_user_by_telegram_id(effective_telegram_id)
            if not user:
                await message.answer("Сначала отправьте /start.")
                return
            await BotUserFacade(session).activate_trial(user.id)
            await notify_admin(bot, session, f"Trial activated: user_id={user.id}")
            await session.commit()
        except TrialError as exc:
            await session.rollback()
            await message.answer(_trial_error_text(str(exc)), reply_markup=keyboards.back_menu())
            return
        except Exception as exc:
            await session.rollback()
            logger.warning("bot_trial_failed", error=str(exc), telegram_id=effective_telegram_id)
            await notify_admin(
                bot,
                session,
                f"Trial activation error: telegram_id={effective_telegram_id}, error={exc}",
            )
            await session.commit()
            await message.answer("Не удалось активировать пробный доступ. Попробуйте позже.")
            return
    await message.answer(ru.TRIAL_STARTED, reply_markup=keyboards.after_payment_menu())


def _trial_error_text(error: str) -> str:
    lowered = error.lower()
    if "already" in lowered:
        return ru.TRIAL_USED
    if "not configured" in lowered:
        return ru.TRIAL_NOT_CONFIGURED
    if "blocked" in lowered:
        return "Заблокированный пользователь не может получить пробный доступ."
    return "Пробный период временно недоступен."
