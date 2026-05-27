from decimal import Decimal

from app.core.enums import PaymentProviderType
from app.services.billing.providers.base import InvoiceRequest, InvoiceResult


class TelegramStarsProvider:
    provider = PaymentProviderType.TELEGRAM_STARS

    def __init__(self, *, stars_per_rub: int) -> None:
        self.stars_per_rub = stars_per_rub

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        stars_amount = int((request.amount * self.stars_per_rub).to_integral_value())
        payload = {
            "title": request.description[:32] or "VPN",
            "description": request.description,
            "payload": request.order_id,
            "currency": "XTR",
            "prices": [{"label": request.description[:32] or "VPN", "amount": stars_amount}],
        }
        return InvoiceResult(
            provider=self.provider,
            provider_invoice_id=request.order_id,
            payment_url=None,
            raw=payload,
        )

    async def check_payment(self, provider_payment_id: str) -> dict:
        return {"provider_payment_id": provider_payment_id, "status": "handled_by_telegram_bot"}

    async def refund(self, provider_payment_id: str, amount: Decimal | None = None) -> dict:
        return {
            "provider_payment_id": provider_payment_id,
            "amount": str(amount) if amount is not None else None,
            "status": "manual_refund_required",
        }
