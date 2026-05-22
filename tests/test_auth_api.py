from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.api.main import app
from app.core.enums import AdminRole
from app.core.security import hash_password
from app.db.base import Base
from app.db.models.admin import AdminUser


async def test_admin_login_and_profile() -> None:
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
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
