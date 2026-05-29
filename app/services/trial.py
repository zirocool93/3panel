from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditActorType, AuditEntityType, PaymentProviderType
from app.db.models.billing import Order
from app.db.models.user import User
from app.services.audit import add_audit_log
from app.services.orders import OrderService
from app.services.payments import PaymentService


class TrialError(ValueError):
    pass


class TrialService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def activate_trial(self, user_id: int) -> Order:
        from sqlalchemy import select

        from app.db.models.tariff import Tariff

        user = await self.session.get(User, user_id)
        if not user:
            raise TrialError("User not found.")
        if user.is_blocked:
            raise TrialError("Blocked user cannot activate trial.")
        if user.is_trial_used:
            raise TrialError("Trial already used.")
        result = await self.session.execute(
            select(Tariff).where(Tariff.enabled.is_(True), Tariff.is_trial.is_(True)).limit(1)
        )
        tariff = result.scalar_one_or_none()
        if not tariff:
            raise TrialError("Trial tariff not configured.")
        order = await OrderService(self.session).create_order(
            user_id=user.id,
            tariff_id=tariff.id,
            payment_method=PaymentProviderType.BALANCE,
            allow_hidden_plan=True,
            metadata={"trial": True},
        )
        order.amount = Decimal("0")
        payment = await PaymentService(self.session).create_payment(
            order_id=order.id, provider=PaymentProviderType.BALANCE
        )
        await PaymentService(self.session).mark_succeeded(
            payment_id=payment.id,
            provider=PaymentProviderType.BALANCE,
            amount=0,
            currency=order.currency,
        )
        user.is_trial_used = True
        add_audit_log(
            self.session,
            action="trial.activated",
            entity_type=AuditEntityType.USER,
            entity_id=user.id,
            actor_type=AuditActorType.USER,
            actor_id=user.id,
        )
        return order
