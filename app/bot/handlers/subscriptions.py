from datetime import UTC, datetime
from typing import Any

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.texts import ru
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.services.bot_facades import BotSubscriptionFacade, BotUserFacade

router = Router(name="subscriptions")
logger = structlog.get_logger(__name__)


@router.message(Command("vpn"))
async def vpn_command(message: Message) -> None:
    await show_vpn(message)


@router.callback_query(F.data == "vpn:show")
async def vpn_callback(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await show_vpn(callback.message, telegram_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("sub:link:"))
async def subscription_link_callback(callback: CallbackQuery) -> None:
    subscription_id = _callback_int(callback.data)
    if subscription_id is None:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return
    async with async_session_factory() as session:
        user = await BotUserFacade(session).get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала отправьте /start.", show_alert=True)
            return
        link = public_subscription_url(subscription_id=None, token=None)
        subscription = next(
            (
                item
                for item in await BotUserFacade(session).get_my_vpn(user.id)
                if item.id == subscription_id
            ),
            None,
        )
        if subscription:
            link = public_subscription_url(
                subscription_id=subscription.id,
                token=subscription.subscription_token,
            )
        if not link:
            link = await BotSubscriptionFacade(session).get_subscription_link(
                user.id,
                subscription_id,
            )
    if not link:
        await callback.answer("Ссылка ещё создаётся.", show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(f"Subscription link:\n<code>{link}</code>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("sub:qr:"))
async def subscription_qr_callback(callback: CallbackQuery) -> None:
    await callback.answer("QR-код будет добавлен в следующем обновлении.", show_alert=True)


async def show_vpn(message: Message, telegram_id: int | None = None) -> None:
    effective_telegram_id = telegram_id or (message.from_user.id if message.from_user else None)
    if effective_telegram_id is None:
        return
    async with async_session_factory() as session:
        user = await BotUserFacade(session).get_user_by_telegram_id(effective_telegram_id)
        if not user:
            await message.answer("Сначала отправьте /start.")
            return
        subscriptions = await BotUserFacade(session).get_my_vpn(user.id)
    active_subscriptions = [
        item for item in subscriptions if item.expires_at is None or _not_expired(item.expires_at)
    ]
    if not active_subscriptions:
        await message.answer(ru.NO_ACTIVE_VPN, reply_markup=keyboards.empty_vpn_menu())
        return
    for subscription in active_subscriptions:
        await message.answer(
            _subscription_text(subscription),
            reply_markup=keyboards.subscription_menu(subscription.id),
            parse_mode="HTML",
        )


def public_subscription_url(subscription_id: int | None, token: str | None) -> str | None:
    if not token:
        return None
    base_url = get_settings().subscription_public_base_url.rstrip("/")
    if not base_url:
        return None
    return f"{base_url}/sub/{token}"


def _subscription_text(subscription: Any) -> str:
    countries = sorted(
        {node.server.country for node in subscription.nodes if node.server and node.server.country}
    )
    traffic = (
        "безлимит"
        if subscription.traffic_limit_bytes is None
        else f"{subscription.traffic_used_bytes} / {subscription.traffic_limit_bytes} байт"
    )
    expires_at = (
        subscription.expires_at.strftime("%Y-%m-%d") if subscription.expires_at else "без срока"
    )
    link = public_subscription_url(subscription.id, subscription.subscription_token)
    return (
        f"<b>{subscription.tariff.name if subscription.tariff else 'VPN'}</b>\n"
        f"Статус: {subscription.status.value}\n"
        f"Действует до: {expires_at}\n"
        f"Устройств: {subscription.device_limit or 'без ограничений'}\n"
        f"Трафик: {traffic}\n"
        f"Страны: {', '.join(countries) if countries else 'не указаны'}\n"
        f"Нод: {len(subscription.nodes)}\n"
        f"Ссылка: <code>{link or 'создаётся'}</code>"
    )


def _not_expired(value: datetime) -> bool:
    now = datetime.now(UTC)
    if value.tzinfo is None:
        now = now.replace(tzinfo=None)
    return value > now


def _callback_int(data: str | None) -> int | None:
    if not data:
        return None
    raw = data.rsplit(":", 1)[-1]
    return int(raw) if raw.isdigit() else None
