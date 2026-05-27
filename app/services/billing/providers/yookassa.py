from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import httpx

from app.core.enums import PaymentProviderType
from app.services.billing.providers.base import InvoiceRequest, InvoiceResult


class YooKassaProvider:
    provider = PaymentProviderType.YOOKASSA

    def __init__(
        self,
        *,
        shop_id: str,
        secret_key: str,
        api_base_url: str = "https://api.yookassa.ru/v3",
        timeout: float = 20.0,
    ) -> None:
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        payload: dict[str, Any] = {
            "amount": {"value": _money(request.amount), "currency": request.currency.upper()},
            "capture": True,
            "description": request.description,
            "confirmation": {
                "type": "redirect",
                "return_url": request.return_url or request.success_url,
            },
            "metadata": {"order_id": request.order_id, **(request.metadata or {})},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/payments",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": request.order_id or str(uuid4())},
            )
            response.raise_for_status()
            data = response.json()

        return InvoiceResult(
            provider=self.provider,
            provider_invoice_id=str(data["id"]),
            payment_url=data.get("confirmation", {}).get("confirmation_url"),
            raw=data,
        )

    async def check_payment(self, provider_payment_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/payments/{provider_payment_id}",
                auth=(self.shop_id, self.secret_key),
            )
            response.raise_for_status()
            return cast(dict, response.json())

    async def refund(self, provider_payment_id: str, amount: Decimal | None = None) -> dict:
        payload: dict[str, Any] = {"payment_id": provider_payment_id}
        if amount is not None:
            payload["amount"] = {"value": _money(amount), "currency": "RUB"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/refunds",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": str(uuid4())},
            )
            response.raise_for_status()
            return cast(dict, response.json())


def _money(value: Decimal) -> str:
    return f"{value:.2f}"
