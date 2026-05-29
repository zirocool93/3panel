from datetime import UTC, datetime
from decimal import Decimal
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    AuditActorType,
    AuditEntityType,
    BalanceTransactionType,
    OrderStatus,
    PaymentEventType,
    PaymentProviderType,
    PaymentStatus,
)
from app.db.models.billing import BalanceTransaction, Order, Payment, PaymentEvent
from app.db.models.user import User
from app.schemas.commerce import PaymentRead
from app.services.audit import add_audit_log


class PaymentError(ValueError):
    pass


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_payment(self, *, order_id: int, provider: PaymentProviderType) -> Payment:
        order = await self._get_order(order_id)
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise PaymentError("Order must be pending payment.")
        payment = Payment(
            order_id=order.id,
            user_id=order.user_id,
            provider=provider,
            status=PaymentStatus.PENDING,
            amount=order.amount,
            currency=order.currency,
            idempotency_key=token_urlsafe(32),
        )
        self.session.add(payment)
        await self.session.flush()
        payment.invoice_payload = f"order:{order.id}:payment:{payment.id}:user:{order.user_id}"
        self.session.add(
            PaymentEvent(
                payment_id=payment.id,
                provider=provider,
                event_type=PaymentEventType.INVOICE_CREATED,
                payload={"invoice_payload": payment.invoice_payload},
                created_at=datetime.now(UTC),
            )
        )
        return payment

    async def mark_succeeded(
        self,
        *,
        payment_id: int | None = None,
        external_payment_id: str | None = None,
        provider: PaymentProviderType,
        provider_payload: dict[str, Any] | None = None,
        amount: Decimal | int | None = None,
        currency: str | None = None,
        event_type: PaymentEventType = PaymentEventType.PAYMENT_SUCCEEDED,
        actor_type: AuditActorType = AuditActorType.SYSTEM,
        actor_id: int | str | None = None,
    ) -> Payment:
        payment = await self._find_payment(
            payment_id=payment_id,
            external_payment_id=external_payment_id,
            provider=provider,
        )
        if payment.status == PaymentStatus.SUCCEEDED:
            return payment
        expected_amount = Decimal(payment.amount)
        if amount is not None and Decimal(amount) != expected_amount:
            raise PaymentError("Payment amount mismatch.")
        if currency is not None and currency.upper() != payment.currency.upper():
            raise PaymentError("Payment currency mismatch.")

        now = datetime.now(UTC)
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = now
        payment.provider_payload = provider_payload
        if external_payment_id and not payment.external_payment_id:
            payment.external_payment_id = external_payment_id
        payment.order.status = OrderStatus.PAID
        payment.order.paid_at = payment.order.paid_at or now

        user = await self.session.get(User, payment.user_id)
        if user:
            before = Decimal(user.balance or 0)
            after = before + expected_amount
            user.balance = after
            self.session.add(
                BalanceTransaction(
                    user_id=user.id,
                    type=BalanceTransactionType.PAYMENT.value,
                    payment_method=provider.value,
                    amount=expected_amount,
                    currency=payment.currency.upper(),
                    balance_before=before,
                    balance_after=after,
                    description=f"Payment for order #{payment.order_id}",
                    external_id=payment.external_payment_id,
                )
            )
        self.session.add(
            PaymentEvent(
                payment_id=payment.id,
                provider=provider,
                event_type=event_type,
                external_event_id=external_payment_id,
                payload=provider_payload,
                processed_at=now,
                created_at=now,
            )
        )
        add_audit_log(
            self.session,
            action="payment.succeeded",
            entity_type=AuditEntityType.PAYMENT,
            entity_id=payment.id,
            actor_type=actor_type,
            actor_id=actor_id,
            after={"order_id": payment.order_id, "amount": str(payment.amount)},
        )
        await self.session.flush()
        self._enqueue_provisioning(payment.order_id)
        return payment

    async def mark_failed(
        self,
        *,
        payment_id: int,
        provider_payload: dict[str, Any] | None = None,
        fail_order: bool = False,
    ) -> Payment:
        payment = await self._find_payment(payment_id=payment_id, provider=None)
        payment.status = PaymentStatus.FAILED
        payment.failed_at = datetime.now(UTC)
        payment.provider_payload = provider_payload
        if fail_order:
            payment.order.status = OrderStatus.FAILED
        return payment

    async def mark_expired(self, *, payment_id: int) -> Payment:
        payment = await self._find_payment(payment_id=payment_id, provider=None)
        payment.status = PaymentStatus.EXPIRED
        return payment

    async def refund_payment(self, *, payment_id: int) -> None:
        raise NotImplementedError("Refund flow is provider-specific and not implemented yet.")

    async def _get_order(self, order_id: int) -> Order:
        order = await self.session.get(Order, order_id)
        if not order:
            raise PaymentError("Order not found.")
        return order

    async def _find_payment(
        self,
        *,
        payment_id: int | None = None,
        external_payment_id: str | None = None,
        provider: PaymentProviderType | None,
    ) -> Payment:
        query = select(Payment).options(selectinload(Payment.order))
        if payment_id is not None:
            query = query.where(Payment.id == payment_id)
        elif external_payment_id:
            query = query.where(Payment.external_payment_id == external_payment_id)
        else:
            raise PaymentError("payment_id or external_payment_id is required.")
        if provider is not None:
            query = query.where(Payment.provider == provider)
        result = await self.session.execute(query)
        payment = result.scalar_one_or_none()
        if not payment:
            raise PaymentError("Payment not found.")
        return payment

    def _enqueue_provisioning(self, order_id: int) -> None:
        try:
            from app.workers.tasks.commerce import provision_order_task

            provision_order_task.delay(order_id)
        except Exception:
            pass


def payment_read(payment: Payment) -> PaymentRead:
    return PaymentRead(
        id=payment.id,
        order_id=payment.order_id,
        user_id=payment.user_id,
        provider=payment.provider,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        external_payment_id=payment.external_payment_id,
        invoice_payload=payment.invoice_payload,
        idempotency_key=payment.idempotency_key,
        paid_at=payment.paid_at,
        failed_at=payment.failed_at,
        refunded_at=payment.refunded_at,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )
