from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, settings_dep
from app.core.config import Settings
from app.core.crypto import CredentialEncryptionError, decrypt_secret, encrypt_secret
from app.core.enums import PanelProviderType, ServerHealthStatus
from app.db.models.admin import AdminUser
from app.db.models.server import Server
from app.schemas.servers import (
    ServerCreate,
    ServerHealthRead,
    ServerInboundRead,
    ServerRead,
    ServerUpdate,
)
from app.services.panels.xui import XuiCredentials, XuiProvider
from app.services.panels.xui.exceptions import XuiError

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerRead])
async def list_servers(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[Server]:
    result = await session.execute(select(Server).order_by(Server.priority, Server.id))
    return list(result.scalars())


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> Server:
    server = Server(
        name=payload.name,
        provider_type=PanelProviderType.XUI,
        country=payload.country,
        location=payload.location,
        panel_url=str(payload.panel_url).rstrip("/"),
        username_encrypted=encrypt_secret(payload.username, settings=settings),
        password_encrypted=encrypt_secret(payload.password, settings=settings),
        api_token_encrypted=encrypt_secret(payload.api_token, settings=settings),
        enabled=payload.enabled,
        max_users=payload.max_users,
        priority=payload.priority,
        subscription_base_url=(
            str(payload.subscription_base_url).rstrip("/")
            if payload.subscription_base_url
            else None
        ),
    )
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


@router.patch("/{server_id}", response_model=ServerRead)
async def update_server(
    server_id: int,
    payload: ServerUpdate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> Server:
    server = await _get_server(session, server_id)
    data = payload.model_dump(exclude_unset=True)
    for field in (
        "name",
        "country",
        "location",
        "enabled",
        "max_users",
        "priority",
    ):
        if field in data:
            setattr(server, field, data[field])
    if "panel_url" in data and payload.panel_url:
        server.panel_url = str(payload.panel_url).rstrip("/")
    if "subscription_base_url" in data:
        server.subscription_base_url = (
            str(payload.subscription_base_url).rstrip("/")
            if payload.subscription_base_url
            else None
        )
    if "username" in data:
        server.username_encrypted = encrypt_secret(payload.username, settings=settings)
    if "password" in data:
        server.password_encrypted = encrypt_secret(payload.password, settings=settings)
    if "api_token" in data:
        server.api_token_encrypted = encrypt_secret(payload.api_token, settings=settings)
    await session.commit()
    await session.refresh(server)
    return server


@router.post("/{server_id}/check", response_model=ServerHealthRead)
async def check_server(
    server_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> ServerHealthRead:
    server = await _get_server(session, server_id)
    try:
        async with _provider_for(server, settings=settings) as provider:
            await provider.healthcheck()
        server.last_health_status = ServerHealthStatus.ONLINE
        message = "Подключение к 3X-UI успешно."
        ok = True
    except (CredentialEncryptionError, XuiError) as exc:
        server.last_health_status = ServerHealthStatus.OFFLINE
        message = str(exc)
        ok = False
    server.last_health_checked_at = datetime.now(UTC)
    await session.commit()
    return ServerHealthRead(ok=ok, status=server.last_health_status, message=message)


@router.get("/{server_id}/inbounds", response_model=list[ServerInboundRead])
async def list_inbounds(
    server_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> list[ServerInboundRead]:
    server = await _get_server(session, server_id)
    try:
        async with _provider_for(server, settings=settings) as provider:
            inbounds = await provider.get_inbounds()
    except (CredentialEncryptionError, XuiError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [ServerInboundRead.model_validate(inbound.model_dump()) for inbound in inbounds]


async def _get_server(session: AsyncSession, server_id: int) -> Server:
    server = await session.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сервер не найден.")
    return server


def _provider_for(server: Server, *, settings: Settings) -> XuiProvider:
    username = decrypt_secret(server.username_encrypted, settings=settings)
    password = decrypt_secret(server.password_encrypted, settings=settings)
    api_token = decrypt_secret(server.api_token_encrypted, settings=settings)
    if not api_token and (not username or not password):
        raise CredentialEncryptionError("Для сервера укажите API token или логин и пароль 3X-UI.")
    return XuiProvider(
        XuiCredentials(
            panel_url=server.panel_url,
            username=username,
            password=password,
            api_token=api_token,
        )
    )
