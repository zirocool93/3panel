import structlog
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.bot import keyboards
from app.bot.admin_notify import notify_admin
from app.bot.texts import ru
from app.core.enums import PaymentProviderType
from app.db.session import async_session_factory
from app.services.bot_facades import BotPaymentFacade, BotUserFacade
from app.services.telegram_stars import TelegramStarsError, TelegramStarsService

router = Router(name="payments")
logger = structlog.get_logger(__name__)


@router.callback_query(F.data.startswith("pay:stars:"))
async def pay_stars_callback(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user:
        return
    tariff_id = _callback_int(callback.data)
    if tariff_id is None:
        await callback.answer(ru.TARIFF_UNAVAILABLE, show_alert=True)
        return
    async with async_session_factory() as session:
        user = await BotUserFacade(session).get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала отправьте /start.", show_alert=True)
            return
        tariff = await BotUserFacade(session).get_tariff(
            tariff_id,
            PaymentProviderType.TELEGRAM_STARS,
        )
        if not tariff:
            await callback.answer(ru.TARIFF_UNAVAILABLE, show_alert=True)
            return
        try:
            order, payment = await BotPaymentFacade(session).create_telegram_stars_invoice(
                user.id,
                tariff.id,
            )
            await session.commit()
        except Exception as exc:
            logger.warning("bot_create_stars_invoice_failed", error=str(exc), tariff_id=tariff_id)
            await callback.answer("Не удалось создать платёж.", show_alert=True)
            return

    if callback.message:
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"VPN: {tariff.name}",
            description=tariff.description or f"VPN-доступ на {tariff.duration_days} дн.",
            payload=payment.invoice_payload or "",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=tariff.name, amount=int(order.amount))],
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:manual:"))
async def pay_manual_callback(callback: CallbackQuery) -> None:
    await callback.answer("Ручная оплата появится в следующем обновлении.", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    try:
        TelegramStarsService._parse_payload(pre_checkout_query.invoice_payload)
    except (TelegramStarsError, ValueError) as exc:
        logger.warning("bot_pre_checkout_invalid", error=str(exc))
        await pre_checkout_query.answer(ok=False, error_message="Платёж не найден.")
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot) -> None:
    if not message.from_user or not message.successful_payment:
        return
    payment = message.successful_payment
    async with async_session_factory() as session:
        try:
            await BotPaymentFacade(session).handle_successful_payment(
                telegram_id=message.from_user.id,
                invoice_payload=payment.invoice_payload,
                telegram_payment_charge_id=payment.telegram_payment_charge_id,
                provider_payment_charge_id=payment.provider_payment_charge_id,
                total_amount=payment.total_amount,
                currency=payment.currency,
                raw_payload=payment.model_dump(mode="json"),
            )
            user = await BotUserFacade(session).get_user_by_telegram_id(message.from_user.id)
            subscriptions = await BotUserFacade(session).get_my_vpn(user.id) if user else []
            await notify_admin(
                bot,
                session,
                "Оплата получена: "
                f"telegram_id={message.from_user.id}, amount={payment.total_amount} XTR",
            )
            await session.commit()
        except Exception as exc:
            logger.warning("bot_successful_payment_failed", error=str(exc))
            await notify_admin(
                bot,
                session,
                "Ошибка обработки successful_payment: "
                f"telegram_id={message.from_user.id}, error={exc}",
            )
            await session.commit()
            await message.answer("Оплата получена, но доступ ещё создаётся. Напишите в поддержку.")
            return

    await message.answer(ru.PAYMENT_RECEIVED, reply_markup=keyboards.after_payment_menu())
    if subscriptions:
        await message.answer(
            "Проверьте раздел «Мой VPN». Если ссылка ещё не появилась, "
            "нажмите кнопку через минуту.",
            reply_markup=keyboards.after_payment_menu(),
        )
    else:
        await message.answer(ru.PROVISIONING_PENDING, reply_markup=keyboards.after_payment_menu())


def _callback_int(data: str | None) -> int | None:
    if not data:
        return None
    raw = data.rsplit(":", 1)[-1]
    return int(raw) if raw.isdigit() else None
