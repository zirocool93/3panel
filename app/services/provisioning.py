from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.crypto import CredentialEncryptionError, decrypt_secret
from app.core.enums import (
    AuditEntityType,
    OrderStatus,
    SubscriptionNodeStatus,
    SubscriptionStatus,
)
from app.db.models.billing import Order
from app.db.models.server import Server
from app.db.models.subscription import VpnSubscription, VpnSubscriptionNode
from app.db.models.tariff import Tariff, TariffInbound
from app.services.audit import add_audit_log
from app.services.orders import OrderService
from app.services.panels.xui import XuiCredentials, XuiProvider
from app.services.panels.xui.exceptions import XuiError
from app.services.server_selection import ServerSelectionService


class ProvisioningError(ValueError):
    pass


class SubscriptionProvisioningService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def provision_order(self, order_id: int) -> VpnSubscription:
        order = await self._load_order(order_id)
        existing = await self._existing_for_order(order)
        if existing and existing.status == SubscriptionStatus.ACTIVE:
            return existing
        if order.status not in {OrderStatus.PAID, OrderStatus.PROVISIONING}:
            raise ProvisioningError("Order must be paid before provisioning.")

        await OrderService(self.session).mark_provisioning(order.id)
        subscription = existing or await self._create_or_extend_subscription(order)
        try:
            await self._ensure_nodes(order, subscription)
        except Exception as exc:
            subscription.status = SubscriptionStatus.PROVISIONING_FAILED
            subscription.admin_comment = f"Provisioning failed for order #{order.id}: {exc}"
            await OrderService(self.session).mark_failed(order.id, str(exc))
            raise

        nodes = await self._nodes_for_subscription(subscription.id)
        active_nodes = [node for node in nodes if node.status == SubscriptionNodeStatus.ACTIVE]
        if not active_nodes:
            subscription.status = SubscriptionStatus.PROVISIONING_FAILED
            await OrderService(self.session).mark_failed(order.id, "No active nodes provisioned.")
            raise ProvisioningError("No active nodes provisioned.")
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.is_multi_server = len(active_nodes) > 1
        await OrderService(self.session).mark_fulfilled(order.id)
        metadata = dict(order.metadata_ or {})
        metadata["subscription_id"] = subscription.id
        order.metadata_ = metadata
        add_audit_log(
            self.session,
            action="subscription.provisioned",
            entity_type=AuditEntityType.SUBSCRIPTION,
            entity_id=subscription.id,
            after={"order_id": order.id},
        )
        return subscription

    async def _load_order(self, order_id: int) -> Order:
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.tariff).selectinload(Tariff.prices),
                selectinload(Order.tariff)
                .selectinload(Tariff.inbound_links)
                .selectinload(TariffInbound.server),
                selectinload(Order.tariff).selectinload(Tariff.server_group_links),
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ProvisioningError("Order not found.")
        return order

    async def _existing_for_order(self, order: Order) -> VpnSubscription | None:
        subscription_id = (order.metadata_ or {}).get("subscription_id")
        if not subscription_id:
            return None
        return await self._load_subscription(int(subscription_id))

    async def _create_or_extend_subscription(self, order: Order) -> VpnSubscription:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(VpnSubscription)
            .options(selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server))
            .where(
                VpnSubscription.user_id == order.user_id,
                VpnSubscription.tariff_id == order.tariff_id,
                VpnSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED]),
            )
            .order_by(VpnSubscription.expires_at.desc().nullslast(), VpnSubscription.id.desc())
        )
        subscription = result.scalars().first()
        if subscription:
            base = (
                subscription.expires_at
                if subscription.expires_at and subscription.expires_at > now
                else now
            )
            subscription.expires_at = base + timedelta(days=order.duration_days)
            subscription.status = SubscriptionStatus.PENDING
            subscription.order_id = order.id
        else:
            subscription = VpnSubscription(
                user_id=order.user_id,
                tariff_id=order.tariff_id,
                order_id=order.id,
                status=SubscriptionStatus.PENDING,
                started_at=now,
                expires_at=now + timedelta(days=order.duration_days),
                traffic_limit_bytes=order.traffic_limit_bytes,
                subscription_token=token_urlsafe(32),
                payment_method=order.payment_method.value,
                price_amount=order.amount,
                currency=order.currency,
                duration_days=order.duration_days,
                device_limit=order.device_limit,
            )
            self.session.add(subscription)
            await self.session.flush()
        return subscription

    async def _ensure_nodes(self, order: Order, subscription: VpnSubscription) -> None:
        selected = await ServerSelectionService(self.session).select_for_tariff(order.tariff)
        selected_keys = {(item.server.id, item.inbound_id) for item in selected}
        existing_nodes = await self._nodes_for_subscription(subscription.id)
        for node in existing_nodes:
            if (node.server_id, node.inbound_id) not in selected_keys:
                node.status = SubscriptionNodeStatus.DISABLED
        for item in selected:
            existing_node = next(
                (
                    existing
                    for existing in existing_nodes
                    if (
                        existing.server_id == item.server.id
                        and existing.inbound_id == item.inbound_id
                    )
                ),
                None,
            )
            if existing_node and existing_node.status == SubscriptionNodeStatus.ACTIVE:
                await self._update_node(existing_node, subscription)
                continue
            if existing_node is None:
                node = VpnSubscriptionNode(
                    subscription=subscription,
                    server=item.server,
                    inbound_id=item.inbound_id,
                    protocol=item.protocol,
                    status=SubscriptionNodeStatus.PENDING,
                )
                self.session.add(node)
                await self.session.flush()
                existing_nodes.append(node)
            else:
                node = existing_node
            await self._create_node_client(node, subscription, item.server)

    async def _create_node_client(
        self, node: VpnSubscriptionNode, subscription: VpnSubscription, server: Server
    ) -> None:
        client_uuid = node.client_uuid or str(uuid4())
        email = f"vpnbotx_user_{subscription.user_id}_sub_{subscription.id}_node_{node.id}"
        sub_id = node.sub_id or token_urlsafe(10)
        payload = _xui_payload(
            client_uuid=client_uuid,
            email=email,
            sub_id=sub_id,
            node=node,
            subscription=subscription,
        )
        try:
            async with _provider_for(server, self.settings) as provider:
                ref = await provider.create_client(inbound_id=node.inbound_id, payload=payload)
        except (CredentialEncryptionError, XuiError) as exc:
            node.status = SubscriptionNodeStatus.FAILED
            node.raw_config = {"request": payload, "error": str(exc)}
            raise
        node.client_uuid = client_uuid
        node.email = email
        node.sub_id = sub_id
        node.xui_client_id = ref.external_id
        node.status = SubscriptionNodeStatus.ACTIVE
        node.raw_config = {
            "request": payload,
            "subscription_url": ref.subscription_url,
            "subscription_links": list(ref.subscription_links),
        }

    async def _update_node(self, node: VpnSubscriptionNode, subscription: VpnSubscription) -> None:
        if not node.xui_client_id or not node.server:
            return
        payload = _xui_payload(
            client_uuid=node.client_uuid or str(uuid4()),
            email=node.email or "",
            sub_id=node.sub_id or "",
            node=node,
            subscription=subscription,
        )
        async with _provider_for(node.server, self.settings) as provider:
            await provider.update_client(client_id=node.xui_client_id, payload=payload)

    async def _load_subscription(self, subscription_id: int) -> VpnSubscription | None:
        result = await self.session.execute(
            select(VpnSubscription)
            .options(selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server))
            .where(VpnSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def _nodes_for_subscription(self, subscription_id: int) -> list[VpnSubscriptionNode]:
        result = await self.session.execute(
            select(VpnSubscriptionNode)
            .options(selectinload(VpnSubscriptionNode.server))
            .where(VpnSubscriptionNode.subscription_id == subscription_id)
        )
        return list(result.scalars())


def _provider_for(server: Server, settings: Settings) -> XuiProvider:
    username = decrypt_secret(server.username_encrypted, settings=settings)
    password = decrypt_secret(server.password_encrypted, settings=settings)
    api_token = decrypt_secret(server.api_token_encrypted, settings=settings)
    return XuiProvider(
        XuiCredentials(
            panel_url=server.panel_url,
            username=username,
            password=password,
            api_token=api_token,
        )
    )


def _xui_payload(
    *,
    client_uuid: str,
    email: str,
    sub_id: str,
    node: VpnSubscriptionNode,
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
        "expiryTime": int(subscription.expires_at.timestamp() * 1000)
        if subscription.expires_at
        else 0,
    }
    if node.protocol == "vless":
        payload["flow"] = "xtls-rprx-vision"
    return payload
