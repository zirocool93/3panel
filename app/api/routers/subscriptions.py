from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.enums import SubscriptionStatus
from app.schemas.commerce import SubscriptionInfo
from app.services.subscriptions import SubscriptionService, subscription_links

router = APIRouter(prefix="/sub", tags=["subscriptions"])


@router.get("/{token}", response_class=Response)
async def get_subscription_config(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    subscription = await SubscriptionService(session).get_by_token(token)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    if subscription.user.is_blocked or subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription inactive.")
    if _is_expired(subscription.expires_at):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription expired.")
    if (
        subscription.traffic_limit_bytes
        and subscription.traffic_used_bytes >= subscription.traffic_limit_bytes
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Traffic limit exceeded.")
    return Response("\n".join(subscription_links(subscription)), media_type="text/plain")


@router.get("/{token}/info", response_model=SubscriptionInfo)
async def get_subscription_info(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> SubscriptionInfo:
    subscription = await SubscriptionService(session).get_by_token(token)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    now = datetime.now(UTC)
    is_active = (
        not subscription.user.is_blocked
        and subscription.status == SubscriptionStatus.ACTIVE
        and not _is_expired(subscription.expires_at, now=now)
    )
    return SubscriptionInfo(
        status=subscription.status,
        tariff=subscription.tariff.name if subscription.tariff else None,
        expires_at=subscription.expires_at,
        traffic_used_bytes=subscription.traffic_used_bytes,
        traffic_limit_bytes=subscription.traffic_limit_bytes,
        nodes=len(subscription.nodes),
        server_countries=sorted(
            {
                node.server.country
                for node in subscription.nodes
                if node.server and node.server.country
            }
        ),
        is_active=is_active,
    )


def _is_expired(value: datetime | None, *, now: datetime | None = None) -> bool:
    if value is None:
        return False
    current = now or datetime.now(UTC)
    if value.tzinfo is None:
        current = current.replace(tzinfo=None)
    return value <= current
