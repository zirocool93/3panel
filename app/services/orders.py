from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import AuditActorType, AuditEntityType, OrderStatus, PaymentProviderType
from app.db.models.billing import Order
from app.db.models.tariff import Tariff
from app.db.models.user import User
from app.schemas.commerce import OrderRead
from app.services.audit import add_audit_log
from app.services.tariffs import select_tariff_price


class OrderError(ValueError):
    pass


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_order(
        self,
        *,
        user_id: int,
        tariff_id: int,
        payment_method: PaymentProviderType,
        allow_hidden_plan: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Order:
        user = await self.session.get(User, user_id)
        if not user:
            raise OrderError("User not found.")
        if user.is_blocked:
            raise OrderError("Blocked user cannot create orders.")
        tariff = await self._get_tariff(tariff_id)
        if not tariff.enabled:
            raise OrderError("Tariff is disabled.")
        if not tariff.is_visible and not allow_hidden_plan:
            raise OrderError("Tariff is hidden.")

        amount, currency = select_tariff_price(tariff, payment_method)
        order = Order(
            user_id=user.id,
            tariff_id=tariff.id,
            status=OrderStatus.PENDING_PAYMENT,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            duration_days=tariff.duration_days,
            traffic_limit_bytes=tariff.traffic_limit_gb * 1024**3
            if tariff.traffic_limit_gb
            else None,
            device_limit=tariff.device_limit,
            metadata_=metadata,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        self.session.add(order)
        await self.session.flush()
        add_audit_log(
            self.session,
            action="order.created",
            entity_type=AuditEntityType.ORDER,
            entity_id=order.id,
            actor_type=AuditActorType.USER,
            actor_id=user.id,
            after={"status": order.status.value, "amount": str(order.amount)},
        )
        return order

    async def get_order(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def expire_old_orders(self) -> int:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Order).where(
                Order.status == OrderStatus.PENDING_PAYMENT,
                Order.expires_at.is_not(None),
                Order.expires_at < now,
            )
        )
        expired = 0
        for order in result.scalars():
            order.status = OrderStatus.EXPIRED
            expired += 1
        return expired

    async def mark_paid(self, order_id: int) -> Order:
        order = await self._require_order(order_id)
        if order.status in {OrderStatus.FULFILLED, OrderStatus.PROVISIONING}:
            return order
        order.status = OrderStatus.PAID
        order.paid_at = order.paid_at or datetime.now(UTC)
        return order

    async def mark_provisioning(self, order_id: int) -> Order:
        order = await self._require_order(order_id)
        order.status = OrderStatus.PROVISIONING
        add_audit_log(
            self.session,
            action="provisioning.started",
            entity_type=AuditEntityType.ORDER,
            entity_id=order.id,
            after={"status": order.status.value},
        )
        return order

    async def mark_fulfilled(self, order_id: int) -> Order:
        order = await self._require_order(order_id)
        order.status = OrderStatus.FULFILLED
        order.fulfilled_at = order.fulfilled_at or datetime.now(UTC)
        add_audit_log(
            self.session,
            action="provisioning.fulfilled",
            entity_type=AuditEntityType.ORDER,
            entity_id=order.id,
            after={"status": order.status.value},
        )
        return order

    async def mark_failed(self, order_id: int, reason: str | None = None) -> Order:
        order = await self._require_order(order_id)
        order.status = OrderStatus.FAILED
        data = dict(order.metadata_ or {})
        if reason:
            data["failure_reason"] = reason
        order.metadata_ = data
        add_audit_log(
            self.session,
            action="provisioning.failed",
            entity_type=AuditEntityType.ORDER,
            entity_id=order.id,
            after={"status": order.status.value, "reason": reason},
        )
        return order

    async def cancel_order(self, order_id: int) -> Order:
        order = await self._require_order(order_id)
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(UTC)
        return order

    async def _get_tariff(self, tariff_id: int) -> Tariff:
        result = await self.session.execute(
            select(Tariff).options(selectinload(Tariff.prices)).where(Tariff.id == tariff_id)
        )
        tariff = result.scalar_one_or_none()
        if not tariff:
            raise OrderError("Tariff not found.")
        return tariff

    async def _require_order(self, order_id: int) -> Order:
        order = await self.session.get(Order, order_id)
        if not order:
            raise OrderError("Order not found.")
        return order


def order_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        tariff_id=order.tariff_id,
        status=order.status,
        amount=order.amount,
        currency=order.currency,
        payment_method=order.payment_method,
        duration_days=order.duration_days,
        traffic_limit_bytes=order.traffic_limit_bytes,
        device_limit=order.device_limit,
        metadata=order.metadata_,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        fulfilled_at=order.fulfilled_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
