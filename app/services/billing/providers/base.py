from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.enums import PaymentProviderType


@dataclass(frozen=True)
class InvoiceRequest:
    order_id: str
    amount: Decimal
    currency: str
    description: str
    success_url: str | None = None
    fail_url: str | None = None
    return_url: str | None = None
    customer_email: str | None = None
    metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class InvoiceResult:
    provider: PaymentProviderType
    provider_invoice_id: str
    payment_url: str | None
    raw: dict


class PaymentProvider(Protocol):
    provider: PaymentProviderType

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult: ...

    async def check_payment(self, provider_payment_id: str) -> dict: ...

    async def refund(self, provider_payment_id: str, amount: Decimal | None = None) -> dict: ...
