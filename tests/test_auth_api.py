from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db, settings_dep
from app.api.main import app
from app.core.config import Settings
from app.core.enums import AdminRole
from app.core.security import hash_password
from app.db.base import Base
from app.db.models.admin import AdminUser


async def test_admin_login_and_profile(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            AdminUser(
                email="owner@example.com",
                password_hash=hash_password("long-enough-password"),
                role=AdminRole.OWNER,
            )
        )
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[settings_dep] = lambda: Settings(
        credentials_encryption_key="1eU1yI-x0dUaLYprksH70z9RiPz8AwYI2sf2QSwRJH4="
    )
    sent_test_messages = 0

    async def fake_send_telegram_test_message(_runtime_settings) -> None:
        nonlocal sent_test_messages
        sent_test_messages += 1

    monkeypatch.setattr(
        "app.api.routers.system.send_telegram_test_message",
        fake_send_telegram_test_message,
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await client.post(
                "/api/auth/login",
                json={"email": "owner@example.com", "password": "long-enough-password"},
            )
            assert login_response.status_code == 200

            access_token = login_response.json()["access_token"]
            profile_response = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert profile_response.status_code == 200
            assert profile_response.json()["role"] == "owner"

            update_status_response = await client.get(
                "/api/system/updates",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert update_status_response.status_code == 200
            assert update_status_response.json()["enabled"] is False

            update_start_response = await client.post(
                "/api/system/updates",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert update_start_response.status_code == 409

            settings_response = await client.get(
                "/api/system/telegram-settings",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert settings_response.status_code == 200
            assert settings_response.json()["admin_email"] == "owner@example.com"

            save_settings_response = await client.put(
                "/api/system/telegram-settings",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "bot_username": "my_vpn_bot",
                    "bot_token": "123456:secret",
                    "admin_telegram_id": "123456789",
                    "socks5_enabled": True,
                    "socks5_host": "127.0.0.1",
                    "socks5_port": 1080,
                    "socks5_username": "proxy-user",
                    "socks5_password": "proxy-password",
                    "admin_email": "owner@example.com",
                },
            )
            assert save_settings_response.status_code == 200
            saved_settings = save_settings_response.json()
            assert saved_settings["bot_username"] == "my_vpn_bot"
            assert saved_settings["bot_token_set"] is True
            assert saved_settings["socks5_enabled"] is True
            assert saved_settings["socks5_username_set"] is True

            payment_settings_response = await client.get(
                "/api/payments/settings",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert payment_settings_response.status_code == 200
            assert payment_settings_response.json()["manual_payments_enabled"] is True

            save_payment_settings_response = await client.put(
                "/api/payments/settings",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "manual_payments_enabled": True,
                    "manual_payment_instructions": "Оплата переводом после заявки.",
                    "telegram_stars_enabled": True,
                    "telegram_stars_rate_rub": 2,
                    "telegram_stars_invoice_title": "VPN подписка",
                    "telegram_stars_invoice_description": "Доступ VPNBotX",
                    "cardlink_enabled": True,
                    "cardlink_api_base_url": "https://cardlink.link",
                    "cardlink_shop_id": "shop123",
                    "cardlink_api_token": "cardlink-token",
                    "cardlink_currency": "RUB",
                    "cardlink_locale": "ru",
                    "cardlink_payer_pays_commission": True,
                    "cardlink_success_url": "https://vpn.example.com/payment/success",
                    "cardlink_fail_url": "https://vpn.example.com/payment/fail",
                    "yookassa_enabled": True,
                    "yookassa_shop_id": "123456",
                    "yookassa_secret_key": "yookassa-secret",
                    "yookassa_return_url": "https://vpn.example.com/payment/return",
                    "yookassa_currency": "RUB",
                },
            )
            assert save_payment_settings_response.status_code == 200
            saved_payment_settings = save_payment_settings_response.json()
            assert saved_payment_settings["telegram_stars_enabled"] is True
            assert saved_payment_settings["cardlink_api_token_set"] is True
            assert saved_payment_settings["yookassa_secret_key_set"] is True

            payment_methods_response = await client.get(
                "/api/payments/methods",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert payment_methods_response.status_code == 200
            enabled_methods = {
                method["code"] for method in payment_methods_response.json() if method["enabled"]
            }
            assert {"manual", "telegram_stars", "cardlink", "yookassa"} <= enabled_methods

            test_message_response = await client.post(
                "/api/system/telegram-settings/test-message",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert test_message_response.status_code == 200
            assert test_message_response.json()["ok"] is True
            assert sent_test_messages == 1

            refresh_response = await client.post(
                "/api/auth/refresh",
                json={"refresh_token": login_response.json()["refresh_token"]},
            )
            assert refresh_response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
