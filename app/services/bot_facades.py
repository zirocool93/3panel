from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PaymentProviderType
from app.db.models.user import User
from app.services.orders import OrderService
from app.services.payments import PaymentService
from app.services.subscriptions import SubscriptionService, subscription_links
from app.services.tariffs import TariffCatalogService
from app.services.telegram_stars import TelegramStarsService
from app.services.trial import TrialService
from app.services.users import UserService


class BotUserFacade:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_user(self, telegram_message_data: dict[str, Any], payload: str | None) -> Any:
        return await UserService(self.session).get_or_create_telegram_user(
            telegram_id=int(telegram_message_data["telegram_id"]),
            username=telegram_message_data.get("username"),
            first_name=telegram_message_data.get("first_name"),
            last_name=telegram_message_data.get("last_name"),
            language_code=telegram_message_data.get("language_code"),
            display_name=telegram_message_data.get("display_name"),
            start_payload=payload,
        )

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_main_menu_state(self, user_id: int) -> dict[str, Any]:
        subscriptions = await SubscriptionService(self.session).get_user_active_subscriptions(
            user_id
        )
        return {"active_subscriptions": len(subscriptions)}

    async def get_my_vpn(self, user_id: int) -> Any:
        return await SubscriptionService(self.session).get_user_active_subscriptions(user_id)

    async def get_tariffs(
        self, user_id: int, payment_method: PaymentProviderType | str | None
    ) -> Any:
        return await TariffCatalogService(self.session).get_visible_tariffs(payment_method)

    async def get_tariff(
        self, tariff_id: int, payment_method: PaymentProviderType | str | None
    ) -> Any:
        return await TariffCatalogService(self.session).get_visible_tariff(
            tariff_id, payment_method
        )

    async def create_order_for_tariff(
        self, user_id: int, tariff_id: int, payment_method: PaymentProviderType
    ) -> Any:
        return await OrderService(self.session).create_order(
            user_id=user_id, tariff_id=tariff_id, payment_method=payment_method
        )

    async def activate_trial(self, user_id: int) -> Any:
        return await TrialService(self.session).activate_trial(user_id)

    async def apply_promo_code(self, user_id: int, code: str) -> None:
        raise NotImplementedError("Promo codes are not implemented yet.")

    async def create_support_ticket(self, user_id: int, category: str, message: str) -> None:
        raise NotImplementedError("Support tickets are not implemented yet.")


class BotPaymentFacade:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_telegram_stars_invoice(self, user_id: int, tariff_id: int) -> Any:
        order = await OrderService(self.session).create_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_method=PaymentProviderType.TELEGRAM_STARS,
        )
        payment = await PaymentService(self.session).create_payment(
            order_id=order.id,
            provider=PaymentProviderType.TELEGRAM_STARS,
        )
        return order, payment

    async def handle_successful_payment(self, **kwargs: Any) -> Any:
        return await TelegramStarsService(self.session).handle_successful_payment(**kwargs)

    async def get_payment_status(self, payment_id: int) -> Any:
        from app.db.models.billing import Payment

        payment = await self.session.get(Payment, payment_id)
        return payment.status if payment else None


class BotSubscriptionFacade:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_subscription_link(self, user_id: int, subscription_id: int) -> str | None:
        from app.db.models.subscription import VpnSubscription

        subscription = await self.session.get(VpnSubscription, subscription_id)
        if not subscription or subscription.user_id != user_id:
            return None
        links = subscription_links(subscription)
        return links[0] if links else None

    async def resend_subscription(self, user_id: int, subscription_id: int) -> str | None:
        return await self.get_subscription_link(user_id, subscription_id)

    def get_connection_guides(self, platform: str) -> dict[str, str]:
        return {"platform": platform, "text": "Connection guides will be added in bot UI."}
