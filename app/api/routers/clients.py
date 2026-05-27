from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db
from app.core.enums import BalanceTransactionType, PaymentProviderType, SubscriptionStatus
from app.db.models.admin import AdminUser
from app.db.models.billing import BalanceTransaction
from app.db.models.subscription import VpnSubscription
from app.db.models.tariff import Tariff
from app.db.models.user import User
from app.schemas.clients import (
    ClientBalanceAdjust,
    ClientCreate,
    ClientRead,
    ClientSubscriptionCreate,
    ClientSubscriptionRead,
    ClientTransactionRead,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[ClientRead]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.subscriptions).selectinload(VpnSubscription.tariff),
            selectinload(User.subscriptions).selectinload(VpnSubscription.nodes),
            selectinload(User.balance_transactions),
        )
        .order_by(User.id.desc())
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


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> Response:
    user = await _get_client(session, client_id)
    for transaction in list(user.balance_transactions):
        await session.delete(transaction)
    for subscription in list(user.subscriptions):
        await session.delete(subscription)
    await session.delete(user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{client_id}/subscriptions", response_model=ClientSubscriptionRead)
async def create_client_subscription(
    client_id: int,
    payload: ClientSubscriptionCreate,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientSubscriptionRead:
    user = await _get_client(session, client_id)
    tariff = await session.get(Tariff, payload.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")
    await session.refresh(tariff, ["prices"])
    duration_days = payload.duration_days or tariff.duration_days
    traffic_limit_gb = payload.traffic_limit_gb or tariff.traffic_limit_gb
    price_amount, currency = _subscription_price(tariff, payload)
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
        price_amount=price_amount,
        currency=currency,
        duration_days=duration_days,
        device_limit=(
            payload.device_limit if payload.device_limit is not None else tariff.device_limit
        ),
        admin_comment=payload.admin_comment,
    )
    session.add(subscription)
    if _normal_payment_method(payload.payment_method) == PaymentProviderType.BALANCE.value:
        _add_balance_transaction(
            session=session,
            user=user,
            amount=-price_amount,
            currency=currency,
            transaction_type=BalanceTransactionType.SUBSCRIPTION_CHARGE,
            payment_method=PaymentProviderType.BALANCE,
            admin_id=admin.id,
            subscription=subscription,
            description=f"Списание за подписку: {tariff.name}",
        )
    await session.commit()
    return _subscription_read(subscription)


@router.post("/{client_id}/balance", response_model=ClientRead)
async def adjust_client_balance(
    client_id: int,
    payload: ClientBalanceAdjust,
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientRead:
    user = await _get_client(session, client_id)
    if payload.amount == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Сумма изменения баланса не может быть нулевой.",
        )
    _add_balance_transaction(
        session=session,
        user=user,
        amount=payload.amount,
        currency=payload.currency.upper(),
        transaction_type=BalanceTransactionType.MANUAL_ADJUSTMENT,
        payment_method=None,
        admin_id=admin.id,
        subscription=None,
        description=payload.description,
    )
    await session.commit()
    return _client_read(await _get_client(session, user.id))


@router.get("/{client_id}/transactions", response_model=list[ClientTransactionRead])
async def list_client_transactions(
    client_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[ClientTransactionRead]:
    await _get_client(session, client_id)
    result = await session.execute(
        select(BalanceTransaction)
        .options(selectinload(BalanceTransaction.user))
        .where(BalanceTransaction.user_id == client_id)
        .order_by(BalanceTransaction.id.desc())
    )
    return [_transaction_read(transaction) for transaction in result.scalars()]


async def _get_client(session: AsyncSession, client_id: int) -> User:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.subscriptions).selectinload(VpnSubscription.tariff),
            selectinload(User.subscriptions).selectinload(VpnSubscription.nodes),
            selectinload(User.balance_transactions),
        )
        .where(User.id == client_id)
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
    transactions = [
        _transaction_read(transaction)
        for transaction in sorted(user.balance_transactions, key=lambda item: item.id, reverse=True)
    ]
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
            "transactions": transactions,
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
        nodes_count=len(subscription.nodes) if "nodes" in subscription.__dict__ else 0,
        admin_comment=subscription.admin_comment,
        created_at=subscription.created_at,
    )


def _subscription_price(
    tariff: Tariff, payload: ClientSubscriptionCreate
) -> tuple[Decimal, str]:
    if payload.price_amount is not None:
        return payload.price_amount, (payload.currency or tariff.currency).upper()
    try:
        payment_method = PaymentProviderType(payload.payment_method)
    except ValueError:
        payment_method = PaymentProviderType.MANUAL
    tariff_price = next(
        (
            price
            for price in tariff.prices
            if (
                _normal_payment_method(price.payment_method) == payment_method.value
                and price.enabled
            )
        ),
        None,
    )
    if tariff_price:
        return tariff_price.amount, tariff_price.currency.upper()
    return tariff.price, tariff.currency.upper()


def _add_balance_transaction(
    *,
    session: AsyncSession,
    user: User,
    amount: Decimal,
    currency: str,
    transaction_type: BalanceTransactionType,
    payment_method: PaymentProviderType | None,
    admin_id: int | None,
    subscription: VpnSubscription | None,
    description: str | None,
) -> BalanceTransaction:
    before = user.balance or Decimal("0.00")
    after = before + amount
    user.balance = after
    transaction = BalanceTransaction(
        user=user,
        admin_id=admin_id,
        subscription=subscription,
        type=transaction_type.value,
        payment_method=payment_method.value if payment_method else None,
        amount=amount,
        currency=currency.upper(),
        balance_before=before,
        balance_after=after,
        description=description,
    )
    session.add(transaction)
    return transaction


def transaction_read(transaction: BalanceTransaction) -> ClientTransactionRead:
    return ClientTransactionRead(
        id=transaction.id,
        user_id=transaction.user_id,
        user_display_name=_user_display_name(transaction.user),
        admin_id=transaction.admin_id,
        subscription_id=transaction.subscription_id,
        type=_normal_transaction_type(transaction.type),
        payment_method=_normal_payment_method(transaction.payment_method),
        amount=transaction.amount,
        currency=transaction.currency,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        description=transaction.description,
        external_id=transaction.external_id,
        created_at=transaction.created_at,
    )


_transaction_read = transaction_read


def _user_display_name(user: User | None) -> str | None:
    if not user:
        return None
    return user.display_name or user.username or " ".join(
        part for part in [user.first_name, user.last_name] if part
    )


def _normal_payment_method(value: str | PaymentProviderType | None) -> str | None:
    if value is None:
        return None
    raw = value.value if isinstance(value, PaymentProviderType) else str(value)
    enum_value = PaymentProviderType.__members__.get(raw.upper())
    return enum_value.value if enum_value else raw.lower()


def _normal_transaction_type(value: str | BalanceTransactionType) -> str:
    raw = value.value if isinstance(value, BalanceTransactionType) else str(value)
    enum_value = BalanceTransactionType.__members__.get(raw.upper())
    return enum_value.value if enum_value else raw.lower()
