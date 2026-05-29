from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import SubscriptionNodeStatus, SubscriptionStatus
from app.db.models.subscription import VpnSubscription, VpnSubscriptionNode

logger = structlog.get_logger(__name__)


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_active_subscriptions(self, user_id: int) -> list[VpnSubscription]:
        result = await self.session.execute(
            select(VpnSubscription)
            .options(
                selectinload(VpnSubscription.tariff),
                selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server),
            )
            .where(
                VpnSubscription.user_id == user_id,
                VpnSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(VpnSubscription.expires_at.desc())
        )
        return list(result.scalars().unique())

    async def get_by_token(self, token: str) -> VpnSubscription | None:
        result = await self.session.execute(
            select(VpnSubscription)
            .options(
                selectinload(VpnSubscription.user),
                selectinload(VpnSubscription.tariff),
                selectinload(VpnSubscription.nodes).selectinload(VpnSubscriptionNode.server),
            )
            .where(VpnSubscription.subscription_token == token)
        )
        return result.scalar_one_or_none()

    async def expire_old_subscriptions(self) -> int:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(VpnSubscription).where(
                VpnSubscription.status == SubscriptionStatus.ACTIVE,
                VpnSubscription.expires_at.is_not(None),
                VpnSubscription.expires_at < now,
            )
        )
        count = 0
        for subscription in result.scalars():
            subscription.status = SubscriptionStatus.EXPIRED
            count += 1
        return count

    async def disable_subscription(self, subscription_id: int) -> VpnSubscription:
        subscription = await self.session.get(VpnSubscription, subscription_id)
        if not subscription:
            raise ValueError("Subscription not found.")
        subscription.status = SubscriptionStatus.DISABLED
        return subscription

    async def sync_node_stats(self) -> int:
        return 0


def subscription_links(subscription: VpnSubscription) -> list[str]:
    links: list[str] = []
    for node in subscription.nodes:
        if node.status != SubscriptionNodeStatus.ACTIVE:
            continue
        if not isinstance(node.raw_config, dict):
            continue
        raw_links = node.raw_config.get("subscription_links")
        if isinstance(raw_links, list):
            links.extend(str(link) for link in raw_links if link)
        elif node.raw_config.get("subscription_url"):
            links.append(str(node.raw_config["subscription_url"]))
    seen: set[str] = set()
    result: list[str] = []
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        result.append(link)
    return result
