from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.api.main import app
from app.core.enums import (
    OrderStatus,
    PaymentProviderType,
    PaymentStatus,
    ServerHealthStatus,
    SubscriptionNodeStatus,
    SubscriptionStatus,
)
from app.db.base import Base
from app.db.models.billing import BalanceTransaction
from app.db.models.server import Server
from app.db.models.subscription import VpnSubscription, VpnSubscriptionNode
from app.db.models.tariff import Tariff, TariffInbound, TariffPrice
from app.db.models.user import User
from app.services.bot_facades import BotPaymentFacade
from app.services.orders import OrderError, OrderService
from app.services.panels.base import PanelClientRef
from app.services.payments import PaymentError, PaymentService
from app.services.provisioning import SubscriptionProvisioningService
from app.services.telegram_stars import TelegramStarsService
from app.services.trial import TrialError, TrialService
from app.services.users import UserService


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, factory


async def test_telegram_user_deep_links_and_referrer() -> None:
    engine, factory = await _session_factory()
    try:
        async with factory() as session:
            referrer = User(telegram_id=1, display_name="Ref")
            session.add(referrer)
            await session.flush()
            user = await UserService(session).get_or_create_telegram_user(
                telegram_id=2,
                username="old",
                first_name="Old",
                last_name=None,
                language_code="ru",
                display_name="Old",
                start_payload=f"ref_{referrer.id}",
            )
            await session.flush()
            assert user.referrer_id == referrer.id

            same_user = await UserService(session).get_or_create_telegram_user(
                telegram_id=2,
                username="new",
                first_name="New",
                last_name=None,
                language_code="en",
                display_name="New",
                start_payload="ref_999",
            )
            assert same_user.username == "new"
            assert same_user.referrer_id == referrer.id

            await UserService(session).get_or_create_telegram_user(
                telegram_id=2,
                username="new",
                first_name="New",
                last_name=None,
                language_code="en",
                display_name="New",
                start_payload=f"ref_{user.id}",
            )
            assert same_user.referrer_id == referrer.id

            sourced = await UserService(session).get_or_create_telegram_user(
                telegram_id=3,
                start_payload="source_blogger1",
            )
            assert sourced.source == "blogger1"

            promo = await UserService(session).get_or_create_telegram_user(
                telegram_id=4,
                start_payload="promo_START50",
            )
            assert promo.start_payload == "promo_START50"

            plan = await UserService(session).get_or_create_telegram_user(
                telegram_id=5,
                start_payload="plan_5",
            )
            assert plan.start_payload == "plan_5"
    finally:
        await engine.dispose()


async def test_bot_payment_facade_creates_order_and_payment() -> None:
    engine, factory = await _session_factory()
    try:
        async with factory() as session:
            user = User(telegram_id=100, display_name="Buyer")
            tariff = Tariff(
                name="Stars",
                duration_days=30,
                price=Decimal("300.00"),
                currency="RUB",
                enabled=True,
                is_visible=True,
                prices=[
                    TariffPrice(
                        payment_method=PaymentProviderType.TELEGRAM_STARS.value,
                        amount=Decimal("10.00"),
                        currency="XTR",
                        enabled=True,
                    )
                ],
            )
            session.add_all([user, tariff])
            await session.flush()

            order, payment = await BotPaymentFacade(session).create_telegram_stars_invoice(
                user.id,
                tariff.id,
            )

            assert order.status == OrderStatus.PENDING_PAYMENT
            assert order.amount == Decimal("10.00")
            assert payment.provider == PaymentProviderType.TELEGRAM_STARS
            expected_payload = f"order:{order.id}:payment:{payment.id}:user:{user.id}"
            assert payment.invoice_payload == expected_payload
    finally:
        await engine.dispose()


async def test_order_snapshots_price_and_rejects_blocked_or_disabled() -> None:
    engine, factory = await _session_factory()
    try:
        async with factory() as session:
            user = User(telegram_id=10, display_name="Buyer")
            blocked = User(telegram_id=11, display_name="Blocked", is_blocked=True)
            tariff = Tariff(
                name="Month",
                duration_days=30,
                price=Decimal("300.00"),
                currency="RUB",
                enabled=True,
                is_visible=True,
                prices=[
                    TariffPrice(
                        payment_method=PaymentProviderType.TELEGRAM_STARS.value,
                        amount=Decimal("600.00"),
                        currency="XTR",
                        enabled=True,
                    )
                ],
            )
            disabled = Tariff(
                name="Disabled",
                duration_days=30,
                price=Decimal("1.00"),
                currency="RUB",
                enabled=False,
                is_visible=True,
            )
            session.add_all([user, blocked, tariff, disabled])
            await session.flush()

            order = await OrderService(session).create_order(
                user_id=user.id,
                tariff_id=tariff.id,
                payment_method=PaymentProviderType.TELEGRAM_STARS,
            )
            tariff.prices[0].amount = Decimal("999.00")
            assert order.amount == Decimal("600.00")
            assert order.currency == "XTR"
            assert order.duration_days == 30
            assert order.status == OrderStatus.PENDING_PAYMENT

            try:
                await OrderService(session).create_order(
                    user_id=blocked.id,
                    tariff_id=tariff.id,
                    payment_method=PaymentProviderType.MANUAL,
                )
            except OrderError:
                pass
            else:
                raise AssertionError("blocked user order was allowed")

            try:
                await OrderService(session).create_order(
                    user_id=user.id,
                    tariff_id=disabled.id,
                    payment_method=PaymentProviderType.MANUAL,
                )
            except OrderError:
                pass
            else:
                raise AssertionError("disabled tariff order was allowed")
    finally:
        await engine.dispose()


async def test_payment_success_is_idempotent_and_provisions_once(monkeypatch) -> None:
    engine, factory = await _session_factory()
    created_payloads: list[dict[str, object]] = []

    class FakeXuiProvider:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeXuiProvider":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def create_client(
            self, *, inbound_id: str | None = None, payload: dict[str, object]
        ) -> PanelClientRef:
            created_payloads.append({"inbound_id": inbound_id, **payload})
            return PanelClientRef(
                external_id=f"{inbound_id}:{payload['id']}:{payload['email']}",
                subscription_url=f"vless://{payload['id']}@vpn.example:443#{payload['email']}",
                subscription_links=(f"vless://{payload['id']}@vpn.example:443#{payload['email']}",),
            )

    monkeypatch.setattr("app.services.provisioning.XuiProvider", FakeXuiProvider)
    monkeypatch.setattr(
        "app.services.payments.PaymentService._enqueue_provisioning",
        lambda self, order_id: None,
    )
    try:
        async with factory() as session:
            user = User(telegram_id=20, display_name="Buyer")
            server = Server(
                name="DE",
                country="DE",
                panel_url="https://xui.example",
                enabled=True,
                last_health_status=ServerHealthStatus.ONLINE,
            )
            tariff = Tariff(
                name="Month",
                duration_days=30,
                price=Decimal("300.00"),
                currency="RUB",
                enabled=True,
                is_visible=True,
            )
            session.add_all([user, server, tariff])
            await session.flush()
            session.add(
                TariffInbound(
                    tariff_id=tariff.id,
                    server_id=server.id,
                    inbound_id="101",
                    protocol="vless",
                )
            )
            await session.flush()
            order = await OrderService(session).create_order(
                user_id=user.id,
                tariff_id=tariff.id,
                payment_method=PaymentProviderType.MANUAL,
            )
            payment = await PaymentService(session).create_payment(
                order_id=order.id,
                provider=PaymentProviderType.MANUAL,
            )
            await PaymentService(session).mark_succeeded(
                payment_id=payment.id,
                provider=PaymentProviderType.MANUAL,
                amount=Decimal("300.00"),
                currency="RUB",
            )
            await PaymentService(session).mark_succeeded(
                payment_id=payment.id,
                provider=PaymentProviderType.MANUAL,
                amount=Decimal("300.00"),
                currency="RUB",
            )
            assert payment.status == PaymentStatus.SUCCEEDED
            assert order.status == OrderStatus.PAID
            assert len((await session.execute(select(BalanceTransaction))).scalars().all()) == 1

            subscription = await SubscriptionProvisioningService(session).provision_order(order.id)
            await SubscriptionProvisioningService(session).provision_order(order.id)
            result = await session.execute(select(VpnSubscription))
            assert len(result.scalars().all()) == 1
            assert subscription.status == SubscriptionStatus.ACTIVE
            assert order.status == OrderStatus.FULFILLED
            assert len(created_payloads) == 1

            try:
                failed_order = await OrderService(session).create_order(
                    user_id=user.id,
                    tariff_id=tariff.id,
                    payment_method=PaymentProviderType.MANUAL,
                )
                failed_payment = await PaymentService(session).create_payment(
                    order_id=failed_order.id,
                    provider=PaymentProviderType.MANUAL,
                )
                await PaymentService(session).mark_succeeded(
                    payment_id=failed_payment.id,
                    provider=PaymentProviderType.MANUAL,
                    amount=Decimal("1.00"),
                    currency="RUB",
                )
            except PaymentError:
                pass
            else:
                raise AssertionError("wrong amount was accepted")
    finally:
        await engine.dispose()


async def test_telegram_stars_successful_payment_is_idempotent(monkeypatch) -> None:
    engine, factory = await _session_factory()
    monkeypatch.setattr(
        "app.services.payments.PaymentService._enqueue_provisioning",
        lambda self, order_id: None,
    )
    try:
        async with factory() as session:
            user = User(telegram_id=200, display_name="Stars Buyer")
            tariff = Tariff(
                name="Stars",
                duration_days=30,
                price=Decimal("10.00"),
                currency="XTR",
                enabled=True,
                is_visible=True,
            )
            session.add_all([user, tariff])
            await session.flush()
            order = await OrderService(session).create_order(
                user_id=user.id,
                tariff_id=tariff.id,
                payment_method=PaymentProviderType.TELEGRAM_STARS,
            )
            payment = await PaymentService(session).create_payment(
                order_id=order.id,
                provider=PaymentProviderType.TELEGRAM_STARS,
            )

            for _ in range(2):
                result = await TelegramStarsService(session).handle_successful_payment(
                    telegram_id=user.telegram_id,
                    invoice_payload=payment.invoice_payload or "",
                    telegram_payment_charge_id="tg-charge-1",
                    provider_payment_charge_id="provider-charge-1",
                    total_amount=10,
                    currency="XTR",
                    raw_payload={"ok": True},
                )
                assert result.id == payment.id

            assert payment.status == PaymentStatus.SUCCEEDED
            assert order.status == OrderStatus.PAID
            assert len((await session.execute(select(BalanceTransaction))).scalars().all()) == 1
    finally:
        await engine.dispose()


async def test_trial_can_be_activated_once(monkeypatch) -> None:
    engine, factory = await _session_factory()
    monkeypatch.setattr(
        "app.services.payments.PaymentService._enqueue_provisioning",
        lambda self, order_id: None,
    )
    try:
        async with factory() as session:
            user = User(telegram_id=300, display_name="Trial")
            trial_tariff = Tariff(
                name="Trial",
                duration_days=3,
                price=Decimal("0.00"),
                currency="RUB",
                enabled=True,
                is_visible=True,
                is_trial=True,
            )
            session.add_all([user, trial_tariff])
            await session.flush()

            order = await TrialService(session).activate_trial(user.id)
            assert order.amount == Decimal("0")
            assert user.is_trial_used is True

            try:
                await TrialService(session).activate_trial(user.id)
            except TrialError:
                pass
            else:
                raise AssertionError("second trial activation was allowed")
    finally:
        await engine.dispose()


async def test_subscription_endpoint_active_expired_blocked_invalid() -> None:
    engine, factory = await _session_factory()

    async def override_get_db():
        async with factory() as session:
            yield session

    try:
        async with factory() as session:
            user = User(telegram_id=30, display_name="User")
            server = Server(name="DE", country="DE", panel_url="https://xui.example")
            subscription = VpnSubscription(
                user=user,
                tariff_id=None,
                status=SubscriptionStatus.ACTIVE,
                started_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                subscription_token="token-active",
                traffic_used_bytes=0,
            )
            subscription.nodes.append(
                VpnSubscriptionNode(
                    server=server,
                    inbound_id="101",
                    protocol="vless",
                    status=SubscriptionNodeStatus.ACTIVE,
                    raw_config={"subscription_url": "vless://example"},
                )
            )
            session.add(subscription)
            await session.commit()

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sub/token-active")
            assert response.status_code == 200
            assert response.text == "vless://example"

            info = await client.get("/sub/token-active/info")
            assert info.status_code == 200
            assert info.json()["is_active"] is True

            async with factory() as session:
                result = await session.execute(
                    select(VpnSubscription).where(
                        VpnSubscription.subscription_token == "token-active"
                    )
                )
                sub = result.scalar_one()
                sub.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()
            assert (await client.get("/sub/token-active")).status_code == 403

            async with factory() as session:
                result = await session.execute(
                    select(VpnSubscription).where(
                        VpnSubscription.subscription_token == "token-active"
                    )
                )
                sub = result.scalar_one()
                sub.expires_at = datetime.now(UTC) + timedelta(days=1)
                user = await session.get(User, sub.user_id)
                assert user is not None
                user.is_blocked = True
                await session.commit()
            assert (await client.get("/sub/token-active")).status_code == 403
            assert (await client.get("/sub/missing")).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
