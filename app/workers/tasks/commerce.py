import asyncio

from app.db.session import async_session_factory
from app.services.provisioning import SubscriptionProvisioningService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.commerce.provision_order")
def provision_order_task(order_id: int) -> int:
    async def _run() -> int:
        async with async_session_factory() as session:
            subscription = await SubscriptionProvisioningService(session).provision_order(order_id)
            await session.commit()
            return subscription.id

    return asyncio.run(_run())
