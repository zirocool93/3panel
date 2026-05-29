from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import PaymentProviderType
from app.db.models.billing import Order, Payment
from app.db.models.user import User
from app.services.payments import PaymentService


class TelegramStarsError(ValueError):
    pass


class TelegramStarsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def create_invoice_payload(order_id: int, user_id: int, payment_id: int) -> str:
        return f"order:{order_id}:payment:{payment_id}:user:{user_id}"

    async def handle_successful_payment(
        self,
        *,
        telegram_id: int,
        invoice_payload: str,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str | None,
        total_amount: int,
        currency: str,
        raw_payload: dict[str, Any],
    ) -> Payment:
        if currency.upper() != "XTR":
            raise TelegramStarsError("Telegram Stars currency must be XTR.")
        order_id, payment_id, user_id = self._parse_payload(invoice_payload)
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.order))
            .where(Payment.id == payment_id, Payment.order_id == order_id)
        )
        payment = result.scalar_one_or_none()
        user = await self.session.get(User, user_id)
        order = await self.session.get(Order, order_id)
        if not payment or not user or not order:
            raise TelegramStarsError("Invoice payload points to missing entities.")
        if user.telegram_id != telegram_id:
            raise TelegramStarsError("Telegram user mismatch.")
        if Decimal(total_amount) != Decimal(payment.amount):
            raise TelegramStarsError("Telegram Stars amount mismatch.")
        external_payment_id = telegram_payment_charge_id or provider_payment_charge_id
        return await PaymentService(self.session).mark_succeeded(
            payment_id=payment.id,
            provider=PaymentProviderType.TELEGRAM_STARS,
            provider_payload=raw_payload,
            amount=total_amount,
            currency=currency,
            external_payment_id=external_payment_id,
        )

    @staticmethod
    def _parse_payload(payload: str) -> tuple[int, int, int]:
        parts = payload.split(":")
        if len(parts) != 6 or parts[0] != "order" or parts[2] != "payment" or parts[4] != "user":
            raise TelegramStarsError("Invalid invoice payload.")
        return int(parts[1]), int(parts[3]), int(parts[5])
