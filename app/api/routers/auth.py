from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
    verify_token_hash,
)
from app.db.models.admin import AdminRefreshToken, AdminUser
from app.schemas.auth import AdminMe, LoginRequest, RefreshRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> TokenPair:
    result = await session.execute(
        select(AdminUser).where(AdminUser.email == payload.email.lower())
    )
    admin = result.scalar_one_or_none()
    if (
        not admin
        or not admin.is_active
        or not verify_password(payload.password, admin.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    admin.last_login_at = datetime.now(UTC)
    token_pair = _issue_token_pair(admin=admin, settings=settings)
    session.add(
        _refresh_record(admin=admin, refresh_token=token_pair.refresh_token, settings=settings)
    )
    await session.commit()
    return token_pair


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> TokenPair:
    try:
        token_payload = decode_token(
            payload.refresh_token, expected_type="refresh", settings=settings
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    jti = token_payload.get("jti")
    result = await session.execute(
        select(AdminRefreshToken).where(
            AdminRefreshToken.jti == jti,
            AdminRefreshToken.revoked_at.is_(None),
        )
    )
    refresh_record = result.scalar_one_or_none()
    if (
        not refresh_record
        or refresh_record.expires_at <= datetime.now(UTC)
        or not verify_token_hash(payload.refresh_token, refresh_record.token_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is revoked."
        )

    admin = await session.get(AdminUser, int(token_payload["sub"]))
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin is inactive.",
        )

    refresh_record.revoked_at = datetime.now(UTC)
    token_pair = _issue_token_pair(admin=admin, settings=settings)
    session.add(
        _refresh_record(admin=admin, refresh_token=token_pair.refresh_token, settings=settings)
    )
    await session.commit()
    return token_pair


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> None:
    try:
        token_payload = decode_token(
            payload.refresh_token, expected_type="refresh", settings=settings
        )
    except AuthenticationError:
        return

    result = await session.execute(
        select(AdminRefreshToken).where(AdminRefreshToken.jti == token_payload["jti"])
    )
    refresh_record = result.scalar_one_or_none()
    if refresh_record and verify_token_hash(
        payload.refresh_token,
        refresh_record.token_hash,
    ):
        refresh_record.revoked_at = datetime.now(UTC)
        await session.commit()


@router.get("/me", response_model=AdminMe)
async def me(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return admin


def _issue_token_pair(*, admin: AdminUser, settings: Settings) -> TokenPair:
    refresh_token, _ = create_refresh_token(subject=str(admin.id), settings=settings)
    return TokenPair(
        access_token=create_access_token(subject=str(admin.id), settings=settings),
        refresh_token=refresh_token,
    )


def _refresh_record(
    *, admin: AdminUser, refresh_token: str, settings: Settings
) -> AdminRefreshToken:
    payload = decode_token(refresh_token, expected_type="refresh", settings=settings)
    return AdminRefreshToken(
        admin=admin,
        token_hash=hash_token(refresh_token),
        jti=payload["jti"],
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
        created_at=datetime.now(UTC),
    )
