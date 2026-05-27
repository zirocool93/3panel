from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db
from app.core.enums import SubscriptionStatus
from app.db.models.admin import AdminUser
from app.db.models.subscription import VpnSubscription
from app.db.models.tariff import Tariff
from app.db.models.user import User
from app.schemas.clients import (
    ClientCreate,
    ClientRead,
    ClientSubscriptionCreate,
    ClientSubscriptionRead,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[ClientRead]:
    result = await session.execute(
        select(User).options(selectinload(User.subscriptions)).order_by(User.id.desc())
    )
    return [_client_read(user) for user in result.scalars()]


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientRead:
    if payload.telegram_id is not None:
        await _ensure_telegram_id_free(session, payload.telegram_id)
    user = User(
        display_name=payload.display_name,
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        comment=payload.comment,
    )
    session.add(user)
    await session.commit()
    return _client_read(await _get_client(session, user.id))


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientRead:
    user = await _get_client(session, client_id)
    data = payload.model_dump(exclude_unset=True)
    if "telegram_id" in data and payload.telegram_id != user.telegram_id:
        if payload.telegram_id is not None:
            await _ensure_telegram_id_free(session, payload.telegram_id, exclude_user_id=user.id)
        user.telegram_id = payload.telegram_id
    for field in ("display_name", "username", "first_name", "last_name", "comment", "is_blocked"):
        if field in data:
            setattr(user, field, data[field])
    await session.commit()
    return _client_read(await _get_client(session, user.id))


@router.post("/{client_id}/subscriptions", response_model=ClientSubscriptionRead)
async def create_client_subscription(
    client_id: int,
    payload: ClientSubscriptionCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientSubscriptionRead:
    user = await _get_client(session, client_id)
    tariff = await session.get(Tariff, payload.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")
    duration_days = payload.duration_days or tariff.duration_days
    traffic_limit_gb = payload.traffic_limit_gb or tariff.traffic_limit_gb
    now = datetime.now(UTC)
    subscription = VpnSubscription(
        user=user,
        tariff=tariff,
        status=SubscriptionStatus.PENDING,
        started_at=now,
        expires_at=now + timedelta(days=duration_days),
        traffic_limit_bytes=traffic_limit_gb * 1024**3 if traffic_limit_gb else None,
        subscription_token=token_urlsafe(32),
        is_multi_server=False,
        payment_method=payload.payment_method,
        price_amount=payload.price_amount if payload.price_amount is not None else tariff.price,
        currency=(payload.currency or tariff.currency).upper(),
        duration_days=duration_days,
        device_limit=(
            payload.device_limit if payload.device_limit is not None else tariff.device_limit
        ),
        admin_comment=payload.admin_comment,
    )
    session.add(subscription)
    await session.commit()
    return _subscription_read(subscription)


async def _get_client(session: AsyncSession, client_id: int) -> User:
    result = await session.execute(
        select(User).options(selectinload(User.subscriptions)).where(User.id == client_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден.")
    return user


async def _ensure_telegram_id_free(
    session: AsyncSession, telegram_id: int, exclude_user_id: int | None = None
) -> None:
    query = select(User).where(User.telegram_id == telegram_id)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Клиент с таким Telegram ID уже существует.",
        )


def _client_read(user: User) -> ClientRead:
    subscriptions = [_subscription_read(subscription) for subscription in user.subscriptions]
    return ClientRead.model_validate(
        {
            "id": user.id,
            "display_name": user.display_name,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "comment": user.comment,
            "balance": user.balance,
            "is_blocked": user.is_blocked,
            "subscriptions_count": len(subscriptions),
            "subscriptions": subscriptions,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
    )


def _subscription_read(subscription: VpnSubscription) -> ClientSubscriptionRead:
    tariff = subscription.tariff
    return ClientSubscriptionRead(
        id=subscription.id,
        tariff_id=subscription.tariff_id,
        tariff_name=tariff.name if tariff else None,
        status=subscription.status,
        payment_method=subscription.payment_method,
        price_amount=subscription.price_amount,
        currency=subscription.currency,
        duration_days=subscription.duration_days,
        traffic_limit_gb=(
            subscription.traffic_limit_bytes // 1024**3
            if subscription.traffic_limit_bytes
            else None
        ),
        device_limit=subscription.device_limit,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        subscription_token=subscription.subscription_token,
        nodes_count=len(subscription.nodes),
        admin_comment=subscription.admin_comment,
        created_at=subscription.created_at,
    )
