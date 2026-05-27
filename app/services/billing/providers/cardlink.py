from decimal import Decimal
from typing import Any, cast

import httpx

from app.core.enums import PaymentProviderType
from app.services.billing.providers.base import InvoiceRequest, InvoiceResult


class CardlinkProvider:
    provider = PaymentProviderType.CARDLINK

    def __init__(
        self,
        *,
        api_base_url: str,
        api_token: str,
        shop_id: str,
        locale: str = "ru",
        payer_pays_commission: bool = True,
        timeout: float = 20.0,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_token = api_token
        self.shop_id = shop_id
        self.locale = locale
        self.payer_pays_commission = payer_pays_commission
        self.timeout = timeout

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        data: dict[str, Any] = {
            "amount": _money(request.amount),
            "order_id": request.order_id,
            "description": request.description,
            "type": "normal",
            "shop_id": self.shop_id,
            "currency_in": request.currency.upper(),
            "locale": self.locale,
            "payer_pays_commission": int(self.payer_pays_commission),
        }
        if request.success_url:
            data["success_url"] = request.success_url
        if request.fail_url:
            data["fail_url"] = request.fail_url
        if request.return_url:
            data["return_url"] = request.return_url
        if request.customer_email:
            data["payer_data[email]"] = request.customer_email

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/api/v1/bill/create",
                data=data,
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
            response.raise_for_status()
            payload = response.json()

        return InvoiceResult(
            provider=self.provider,
            provider_invoice_id=str(payload.get("bill_id") or request.order_id),
            payment_url=payload.get("link_page_url") or payload.get("link_url"),
            raw=payload,
        )

    async def check_payment(self, provider_payment_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/api/v1/bill/status",
                params={"id": provider_payment_id},
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
            response.raise_for_status()
            return cast(dict, response.json())

    async def refund(self, provider_payment_id: str, amount: Decimal | None = None) -> dict:
        data: dict[str, Any] = {"payment_id": provider_payment_id}
        if amount is not None:
            data["amount"] = _money(amount)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/api/v1/refund/full/create"
                if amount is None
                else f"{self.api_base_url}/api/v1/refund/partial/create",
                data=data,
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
            response.raise_for_status()
            return cast(dict, response.json())


def _money(value: Decimal) -> str:
    return f"{value:.2f}"
