from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_hex, token_urlsafe
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.crypto import CredentialEncryptionError, decrypt_secret
from app.core.enums import (
    BalanceTransactionType,
    PaymentProviderType,
    SubscriptionNodeStatus,
    SubscriptionStatus,
)
from app.db.models.admin import AdminUser
from app.db.models.billing import BalanceTransaction
from app.db.models.server import Server
from app.db.models.subscription import VpnSubscription, VpnSubscriptionNode
from app.db.models.tariff import Tariff, TariffInbound
from app.db.models.user import User
from app.schemas.clients import (
    ClientBalanceAdjust,
    ClientCreate,
    ClientRead,
    ClientSubscriptionCreate,
    ClientSubscriptionNodeRead,
    ClientSubscriptionRead,
    ClientSubscriptionUpdate,
    ClientTransactionRead,
    ClientUpdate,
)
from app.services.panels.xui import XuiCredentials, XuiProvider
from app.services.panels.xui.exceptions import XuiError
from app.services.qrcode import qr_png_data_url

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
    settings: Settings = Depends(settings_dep),
) -> ClientSubscriptionRead:
    user = await _get_client(session, client_id)
    tariff = await _get_tariff_for_subscription(session, payload.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")
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
    await session.flush()
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
    await _provision_subscription_nodes(
        session=session,
        subscription=subscription,
        tariff=tariff,
        user=user,
        settings=settings,
    )
    await session.commit()
    return _subscription_read(await _get_subscription(session, subscription.id))


@router.patch("/{client_id}/subscriptions/{subscription_id}", response_model=ClientSubscriptionRead)
async def update_client_subscription(
    client_id: int,
    subscription_id: int,
    payload: ClientSubscriptionUpdate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> ClientSubscriptionRead:
    subscription = await _get_client_subscription(session, client_id, subscription_id)
    data = payload.model_dump(exclude_unset=True)
    tariff_changed = False
    tariff = subscription.tariff
    if "tariff_id" in data and payload.tariff_id != subscription.tariff_id:
        if payload.tariff_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Укажите тариф подписки.",
            )
        tariff = await _get_tariff_for_subscription(session, payload.tariff_id)
        if not tariff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")
        subscription.tariff = tariff
        tariff_changed = True

    if "payment_method" in data:
        subscription.payment_method = payload.payment_method
    if "price_amount" in data:
        subscription.price_amount = payload.price_amount
    if "currency" in data:
        subscription.currency = payload.currency.upper() if payload.currency else None
    if "duration_days" in data and payload.duration_days is not None:
        subscription.duration_days = payload.duration_days
        base_date = subscription.started_at or datetime.now(UTC)
        subscription.started_at = base_date
        subscription.expires_at = base_date + timedelta(days=payload.duration_days)
    if "traffic_limit_gb" in data:
        subscription.traffic_limit_bytes = (
            payload.traffic_limit_gb * 1024**3 if payload.traffic_limit_gb else None
        )
    if "device_limit" in data:
        subscription.device_limit = payload.device_limit
    if "admin_comment" in data:
        subscription.admin_comment = payload.admin_comment
    if "status" in data and payload.status is not None:
        subscription.status = payload.status

    if tariff_changed:
        delete_errors = await _delete_subscription_nodes_from_xui(
            subscription=subscription,
            settings=settings,
        )
        if delete_errors:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Не удалось удалить старые клиенты из 3X-UI: " + "; ".join(delete_errors),
            )
        for node in list(subscription.nodes):
            await session.delete(node)
        await session.flush()
        await _provision_subscription_nodes(
            session=session,
            subscription=subscription,
            tariff=tariff,
            user=subscription.user,
            settings=settings,
        )
    else:
        await _sync_subscription_nodes(subscription=subscription, settings=settings)
        _refresh_subscription_status(subscription)

    await session.commit()
    return _subscription_read(await _get_subscription(session, subscription.id))


@router.post(
    "/{client_id}/subscriptions/{subscription_id}/provision",
    response_model=ClientSubscriptionRead,
)
async def provision_client_subscription(
    client_id: int,
    subscription_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> ClientSubscriptionRead:
    subscription = await _get_client_subscription(session, client_id, subscription_id)
    if not subscription.tariff_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У подписки не указан тариф для создания клиентов в 3X-UI.",
        )
    tariff = await _get_tariff_for_subscription(session, subscription.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")

    for node in list(subscription.nodes):
        if node.status != SubscriptionNodeStatus.ACTIVE:
            await session.delete(node)
    await session.flush()
    existing_keys = {(node.server_id, node.inbound_id) for node in subscription.nodes}
    links = [
        link
        for link in tariff.inbound_links
        if (link.server_id, link.inbound_id) not in existing_keys
    ]
    await _provision_subscription_links(
        session=session,
        subscription=subscription,
        tariff=tariff,
        user=subscription.user,
        settings=settings,
        links=links,
    )
    _refresh_subscription_status(subscription)
    await session.commit()
    return _subscription_read(await _get_subscription(session, subscription.id))


@router.delete(
    "/{client_id}/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_client_subscription(
    client_id: int,
    subscription_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> Response:
    subscription = await _get_client_subscription(session, client_id, subscription_id)
    delete_errors = await _delete_subscription_nodes_from_xui(
        subscription=subscription,
        settings=settings,
    )
    if delete_errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось удалить клиентов из 3X-UI: " + "; ".join(delete_errors),
        )
    await session.delete(subscription)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


async def _get_subscription(session: AsyncSession, subscription_id: int) -> VpnSubscription:
    result = await session.execute(
        select(VpnSubscription)
        .options(
            selectinload(VpnSubscription.user),
            selectinload(VpnSubscription.tariff),
            selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server),
        )
        .where(VpnSubscription.id == subscription_id)
    )
    subscription = result.scalar_one()
    return subscription


async def _get_client_subscription(
    session: AsyncSession, client_id: int, subscription_id: int
) -> VpnSubscription:
    result = await session.execute(
        select(VpnSubscription)
        .options(
            selectinload(VpnSubscription.user),
            selectinload(VpnSubscription.tariff),
            selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server),
        )
        .where(VpnSubscription.id == subscription_id, VpnSubscription.user_id == client_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Подписка не найдена.")
    return subscription


async def _get_tariff_for_subscription(session: AsyncSession, tariff_id: int) -> Tariff | None:
    result = await session.execute(
        select(Tariff)
        .options(
            selectinload(Tariff.prices),
            selectinload(Tariff.inbound_links).selectinload(TariffInbound.server),
        )
        .where(Tariff.id == tariff_id)
    )
    return result.scalar_one_or_none()


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
    nodes = [_node_read(node) for node in subscription.nodes]
    subscription_url = next(
        (node.subscription_url for node in nodes if node.subscription_url),
        None,
    )
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
        subscription_url=subscription_url,
        subscription_qr=qr_png_data_url(subscription_url) if subscription_url else None,
        nodes_count=len(nodes),
        nodes=nodes,
        admin_comment=subscription.admin_comment,
        created_at=subscription.created_at,
    )


def _node_read(node: VpnSubscriptionNode) -> ClientSubscriptionNodeRead:
    subscription_url = None
    error = None
    if isinstance(node.raw_config, dict):
        raw_url = node.raw_config.get("subscription_url")
        subscription_url = str(raw_url) if raw_url else None
        raw_error = node.raw_config.get("error")
        error = str(raw_error) if raw_error else None
    return ClientSubscriptionNodeRead(
        id=node.id,
        server_id=node.server_id,
        inbound_id=node.inbound_id,
        protocol=node.protocol,
        email=node.email,
        client_uuid=node.client_uuid,
        sub_id=node.sub_id,
        status=_normal_node_status(node.status),
        subscription_url=subscription_url,
        subscription_qr=qr_png_data_url(subscription_url) if subscription_url else None,
        error=error,
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


async def _provision_subscription_nodes(
    *,
    session: AsyncSession,
    subscription: VpnSubscription,
    tariff: Tariff,
    user: User,
    settings: Settings,
) -> None:
    if not tariff.inbound_links:
        subscription.status = SubscriptionStatus.PENDING
        return

    await _provision_subscription_links(
        session=session,
        subscription=subscription,
        tariff=tariff,
        user=user,
        settings=settings,
        links=list(tariff.inbound_links),
    )


async def _provision_subscription_links(
    *,
    session: AsyncSession,
    subscription: VpnSubscription,
    tariff: Tariff,
    user: User,
    settings: Settings,
    links: list[TariffInbound],
) -> None:
    created_nodes = 0
    failed_nodes = 0
    links_by_server: dict[int, list[TariffInbound]] = defaultdict(list)
    for link in links:
        links_by_server[link.server_id].append(link)

    for server_links in links_by_server.values():
        nodes = await _create_xui_nodes_for_server(
            session=session,
            subscription=subscription,
            user=user,
            tariff=tariff,
            links=server_links,
            settings=settings,
        )
        created_nodes += sum(1 for node in nodes if node.status == SubscriptionNodeStatus.ACTIVE)
        failed_nodes += sum(1 for node in nodes if node.status != SubscriptionNodeStatus.ACTIVE)

    subscription.is_multi_server = created_nodes + failed_nodes > 1
    subscription.status = (
        SubscriptionStatus.ACTIVE if created_nodes else SubscriptionStatus.PROVISIONING_FAILED
    )


async def _sync_subscription_nodes(
    *, subscription: VpnSubscription, settings: Settings
) -> None:
    synced_client_ids: set[str] = set()
    for node in subscription.nodes:
        if node.status not in {SubscriptionNodeStatus.ACTIVE, SubscriptionNodeStatus.DISABLED}:
            continue
        if not node.xui_client_id or not node.server:
            continue
        if node.xui_client_id in synced_client_ids:
            continue
        synced_client_ids.add(node.xui_client_id)
        payload = _xui_update_payload(node=node, subscription=subscription)
        try:
            async with _provider_for(node.server, settings=settings) as provider:
                await provider.update_client(client_id=node.xui_client_id, payload=payload)
        except (CredentialEncryptionError, XuiError) as exc:
            raw_config = dict(node.raw_config or {})
            raw_config["request"] = payload
            raw_config["error"] = str(exc)
            node.raw_config = raw_config
            node.status = SubscriptionNodeStatus.FAILED


async def _delete_subscription_nodes_from_xui(
    *, subscription: VpnSubscription, settings: Settings
) -> list[str]:
    errors: list[str] = []
    deleted_client_ids: set[str] = set()
    for node in subscription.nodes:
        if not node.xui_client_id or not node.server:
            continue
        if node.xui_client_id in deleted_client_ids:
            continue
        deleted_client_ids.add(node.xui_client_id)
        try:
            async with _provider_for(node.server, settings=settings) as provider:
                await provider.delete_client(client_id=node.xui_client_id)
        except (CredentialEncryptionError, XuiError) as exc:
            errors.append(f"{node.email or node.id}: {exc}")
    return errors


def _refresh_subscription_status(subscription: VpnSubscription) -> None:
    if subscription.status == SubscriptionStatus.DISABLED:
        return
    active_nodes = [
        node for node in subscription.nodes if node.status == SubscriptionNodeStatus.ACTIVE
    ]
    failed_nodes = [
        node for node in subscription.nodes if node.status == SubscriptionNodeStatus.FAILED
    ]
    subscription.is_multi_server = len(subscription.nodes) > 1
    if active_nodes:
        subscription.status = SubscriptionStatus.ACTIVE
    elif failed_nodes:
        subscription.status = SubscriptionStatus.PROVISIONING_FAILED


async def _create_xui_nodes_for_server(
    *,
    session: AsyncSession,
    subscription: VpnSubscription,
    user: User,
    tariff: Tariff,
    links: list[TariffInbound],
    settings: Settings,
) -> list[VpnSubscriptionNode]:
    first_link = links[0]
    server = first_link.server
    primary_protocol = (first_link.protocol or "vless").lower()
    client_uuid = str(uuid4())
    email = _xui_client_email(user=user, subscription=subscription, server_id=first_link.server_id)
    sub_id = token_urlsafe(10)
    client_payload = _xui_client_payload(
        client_uuid=client_uuid,
        email=email,
        sub_id=sub_id,
        protocol=_primary_client_protocol(links),
        subscription=subscription,
    )
    nodes: list[VpnSubscriptionNode] = []
    for link in links:
        protocol = (link.protocol or primary_protocol).lower()
        node_payload = _xui_node_payload_for_protocol(client_payload, protocol)
        node = VpnSubscriptionNode(
            subscription=subscription,
            server=server,
            inbound_id=link.inbound_id,
            protocol=protocol,
            client_uuid=client_uuid,
            email=email,
            sub_id=sub_id,
            status=SubscriptionNodeStatus.PENDING,
            raw_config={
                "request": node_payload,
                "inbound_ids": [item.inbound_id for item in links],
            },
        )
        session.add(node)
        nodes.append(node)

    if not server.enabled:
        for node in nodes:
            node.status = SubscriptionNodeStatus.FAILED
            node.raw_config = {
                "request": node.raw_config.get("request") if node.raw_config else client_payload,
                "error": "Сервер отключён.",
            }
        return nodes

    try:
        async with _provider_for(server, settings=settings) as provider:
            ref = await provider.create_client(
                inbound_ids=[link.inbound_id for link in links],
                payload=client_payload,
            )
    except (CredentialEncryptionError, XuiError) as exc:
        for node in nodes:
            node.status = SubscriptionNodeStatus.FAILED
            node.raw_config = {
                "request": node.raw_config.get("request") if node.raw_config else client_payload,
                "error": str(exc),
            }
        return nodes

    for node in nodes:
        node.xui_client_id = ref.external_id
        node.status = SubscriptionNodeStatus.ACTIVE
        node.raw_config = {
            "request": node.raw_config.get("request") if node.raw_config else client_payload,
            "inbound_ids": [item.inbound_id for item in links],
            "subscription_url": ref.subscription_url,
        }
    return nodes


def _xui_client_payload(
    *,
    client_uuid: str,
    email: str,
    sub_id: str,
    protocol: str | None,
    subscription: VpnSubscription,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": client_uuid,
        "email": email,
        "enable": True,
        "subId": sub_id,
        "tgId": 0,
        "reset": 0,
        "limitIp": subscription.device_limit or 0,
        "totalGB": subscription.traffic_limit_bytes or 0,
        "expiryTime": _expiry_millis(subscription.expires_at),
    }
    if protocol == "vless":
        payload["flow"] = "xtls-rprx-vision"
    if protocol and "hysteria" in protocol:
        auth = token_hex(16)
        payload["auth"] = auth
        payload["password"] = auth
    return payload


def _xui_node_payload_for_protocol(
    payload: dict[str, object], protocol: str
) -> dict[str, object]:
    node_payload = dict(payload)
    if protocol == "vless":
        node_payload["flow"] = "xtls-rprx-vision"
    elif protocol != "vless":
        node_payload.pop("flow", None)
    if "hysteria" in protocol and not (node_payload.get("auth") or node_payload.get("password")):
        auth = token_hex(16)
        node_payload["auth"] = auth
        node_payload["password"] = auth
    return node_payload


def _primary_client_protocol(links: list[TariffInbound]) -> str | None:
    protocols = {(link.protocol or "").lower() for link in links}
    if "vless" in protocols:
        return "vless"
    if any("hysteria" in protocol for protocol in protocols):
        return "hysteria"
    return None


def _xui_update_payload(
    *, node: VpnSubscriptionNode, subscription: VpnSubscription
) -> dict[str, object]:
    raw_request = (
        (node.raw_config or {}).get("request")
        if isinstance(node.raw_config, dict)
        else None
    )
    payload = dict(raw_request) if isinstance(raw_request, dict) else {}
    payload.setdefault("id", node.client_uuid or "")
    payload.setdefault("email", node.email or "")
    payload.setdefault("subId", node.sub_id or "")
    payload.setdefault("tgId", 0)
    if payload.get("tgId") in {"", None}:
        payload["tgId"] = 0
    payload.setdefault("reset", 0)
    if node.protocol == "vless":
        payload["flow"] = "xtls-rprx-vision"
    if "hysteria" in node.protocol and not (payload.get("auth") or payload.get("password")):
        auth = token_hex(16)
        payload["auth"] = auth
        payload["password"] = auth
    payload["enable"] = subscription.status not in {
        SubscriptionStatus.DISABLED,
        SubscriptionStatus.EXPIRED,
    }
    payload["limitIp"] = subscription.device_limit or 0
    payload["totalGB"] = subscription.traffic_limit_bytes or 0
    payload["expiryTime"] = _expiry_millis(subscription.expires_at)
    return payload


def _xui_client_email(*, user: User, subscription: VpnSubscription, server_id: int) -> str:
    prefix = user.username or user.display_name or f"user{user.id}"
    safe_prefix = "".join(char for char in prefix.lower() if char.isalnum() or char in {"-", "_"})
    safe_prefix = safe_prefix[:24] or f"user{user.id}"
    return f"{safe_prefix}-{subscription.id}-{server_id}"


def _expiry_millis(value: datetime | None) -> int:
    return int(value.timestamp() * 1000) if value else 0


def _provider_for(server: Server, *, settings: Settings) -> XuiProvider:
    username = decrypt_secret(server.username_encrypted, settings=settings)
    password = decrypt_secret(server.password_encrypted, settings=settings)
    api_token = decrypt_secret(server.api_token_encrypted, settings=settings)
    if not api_token and (not username or not password):
        raise CredentialEncryptionError(
            "Для сервера укажите API token или логин и пароль 3X-UI."
        )
    return XuiProvider(
        XuiCredentials(
            panel_url=server.panel_url,
            username=username,
            password=password,
            api_token=api_token,
        )
    )


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


def _normal_node_status(value: str | SubscriptionNodeStatus) -> str:
    raw = value.value if isinstance(value, SubscriptionNodeStatus) else str(value)
    enum_value = SubscriptionNodeStatus.__members__.get(raw.upper())
    return enum_value.value if enum_value else raw.lower()
