from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.enums import (
    AdminRole,
    PaymentProviderType,
    PaymentStatus,
    ServerHealthStatus,
    SubscriptionStatus,
)
from app.db.models.admin import AdminUser
from app.db.models.billing import Order, Payment
from app.db.models.server import Server
from app.db.models.subscription import VpnSubscription
from app.db.models.user import User
from app.schemas.commerce import (
    DashboardSummary,
    ManualReject,
    OrderCreate,
    OrderRead,
    PaymentCreate,
    PaymentRead,
)
from app.services.orders import OrderError, OrderService, order_read
from app.services.payments import PaymentError, PaymentService, payment_read
from app.services.provisioning import SubscriptionProvisioningService
from app.services.subscriptions import SubscriptionService

router = APIRouter(tags=["commerce"])


@router.get("/orders", response_model=list[OrderRead])
async def list_orders(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    result = await session.execute(select(Order).order_by(Order.id.desc()).limit(500))
    return [order_read(order) for order in result.scalars()]


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> OrderRead:
    try:
        order = await OrderService(session).create_order(
            user_id=payload.user_id,
            tariff_id=payload.tariff_id,
            payment_method=payload.payment_method,
            allow_hidden_plan=payload.allow_hidden_plan,
        )
    except OrderError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return order_read(order)


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> OrderRead:
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order_read(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> OrderRead:
    try:
        order = await OrderService(session).cancel_order(order_id)
    except OrderError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return order_read(order)


@router.post("/orders/{order_id}/retry-provisioning")
async def retry_provisioning(
    order_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> dict[str, int]:
    try:
        service = SubscriptionProvisioningService(session, settings)
        subscription = await service.provision_order(order_id)
    except Exception as exc:
        await session.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return {"subscription_id": subscription.id}


@router.get("/payments", response_model=list[PaymentRead])
async def list_payments(
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    provider: PaymentProviderType | None = None,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[PaymentRead]:
    query = select(Payment).order_by(Payment.id.desc()).limit(500)
    if status_filter is not None:
        query = query.where(Payment.status == status_filter)
    if provider is not None:
        query = query.where(Payment.provider == provider)
    result = await session.execute(query)
    return [payment_read(payment) for payment in result.scalars()]


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> PaymentRead:
    try:
        payment = await PaymentService(session).create_payment(
            order_id=payload.order_id,
            provider=payload.provider,
        )
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return payment_read(payment)


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> PaymentRead:
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    return payment_read(payment)


@router.post("/payments/{payment_id}/manual-confirm", response_model=PaymentRead)
async def manual_confirm(
    payment_id: int,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> PaymentRead:
    _require_accountant(admin)
    try:
        payment = await PaymentService(session).mark_succeeded(
            payment_id=payment_id,
            provider=PaymentProviderType.MANUAL,
            provider_payload={"confirmed_by_admin_id": admin.id},
            actor_id=admin.id,
        )
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return payment_read(payment)


@router.post("/payments/{payment_id}/manual-reject", response_model=PaymentRead)
async def manual_reject(
    payment_id: int,
    payload: ManualReject,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> PaymentRead:
    _require_accountant(admin)
    try:
        payment = await PaymentService(session).mark_failed(
            payment_id=payment_id,
            provider_payload={"rejected_by_admin_id": admin.id, "reason": payload.reason},
            fail_order=False,
        )
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return payment_read(payment)


@router.get("/subscriptions")
async def list_subscriptions(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    result = await session.execute(
        select(VpnSubscription)
        .options(selectinload(VpnSubscription.tariff))
        .order_by(VpnSubscription.id.desc())
        .limit(500)
    )
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "tariff": item.tariff.name if item.tariff else None,
            "status": item.status,
            "expires_at": item.expires_at,
        }
        for item in result.scalars()
    ]


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    subscription = await session.get(VpnSubscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    return {
        "id": subscription.id,
        "status": subscription.status,
        "expires_at": subscription.expires_at,
    }


@router.post("/subscriptions/{subscription_id}/disable")
async def disable_subscription(
    subscription_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    subscription = await SubscriptionService(session).disable_subscription(subscription_id)
    await session.commit()
    return {"id": subscription.id, "status": subscription.status}


@router.post("/subscriptions/{subscription_id}/resync")
async def resync_subscription(subscription_id: int) -> dict[str, object]:
    return {"id": subscription_id, "status": "queued"}


@router.post("/subscriptions/{subscription_id}/resend")
async def resend_subscription(subscription_id: int) -> dict[str, object]:
    return {"id": subscription_id, "status": "todo"}


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return DashboardSummary(
        users_total=await _count(session, User),
        users_new_today=await _count(session, User, User.created_at >= today),
        orders_today=await _count(session, Order, Order.created_at >= today),
        payments_today=await _count(session, Payment, Payment.paid_at >= today),
        revenue_today=await _sum_revenue(session, today),
        revenue_month=await _sum_revenue(session, month),
        active_subscriptions=await _count_active_subscriptions(session),
        expiring_soon=await _count(
            session,
            VpnSubscription,
            VpnSubscription.expires_at <= now + timedelta(days=3),
        ),
        provisioning_failed=await _count(
            session,
            VpnSubscription,
            VpnSubscription.status == SubscriptionStatus.PROVISIONING_FAILED,
        ),
        manual_payments_pending=await _count(
            session,
            Payment,
            Payment.provider == PaymentProviderType.MANUAL,
            Payment.status == PaymentStatus.PENDING,
        ),
        servers_online=await _count(
            session, Server, Server.last_health_status == ServerHealthStatus.ONLINE
        ),
        servers_degraded=await _count(
            session, Server, Server.last_health_status == ServerHealthStatus.DEGRADED
        ),
        servers_offline=await _count(
            session, Server, Server.last_health_status == ServerHealthStatus.OFFLINE
        ),
    )


def _require_accountant(admin: AdminUser) -> None:
    if admin.role not in {AdminRole.OWNER, AdminRole.ADMIN, AdminRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")


async def _count(session: AsyncSession, model: Any, *conditions: Any) -> int:
    query = select(func.count(model.id))
    for condition in conditions:
        query = query.where(condition)
    return int(await session.scalar(query) or 0)


async def _count_active_subscriptions(session: AsyncSession) -> int:
    return await _count(
        session,
        VpnSubscription,
        VpnSubscription.status == SubscriptionStatus.ACTIVE,
    )


async def _sum_revenue(session: AsyncSession, since: datetime) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCEEDED,
            Payment.paid_at >= since,
        )
    )
    return Decimal(value or 0)
