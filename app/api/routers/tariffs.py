from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db
from app.core.enums import PaymentProviderType
from app.db.models.admin import AdminUser
from app.db.models.server import Server
from app.db.models.tariff import Tariff, TariffInbound, TariffPrice
from app.schemas.tariffs import TariffCreate, TariffPriceCreate, TariffRead, TariffUpdate

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@router.get("", response_model=list[TariffRead])
async def list_tariffs(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[TariffRead]:
    result = await session.execute(
        select(Tariff)
        .options(selectinload(Tariff.inbound_links), selectinload(Tariff.prices))
        .order_by(Tariff.sort_order, Tariff.id)
    )
    return [_tariff_read(tariff) for tariff in result.scalars()]


@router.post("", response_model=TariffRead, status_code=status.HTTP_201_CREATED)
async def create_tariff(
    payload: TariffCreate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> TariffRead:
    await _validate_servers(session, [link.server_id for link in payload.inbound_links])
    tariff = Tariff(
        name=payload.name,
        description=payload.description,
        duration_days=payload.duration_days,
        traffic_limit_gb=payload.traffic_limit_gb,
        device_limit=payload.device_limit,
        price=payload.price,
        currency=payload.currency.upper(),
        is_trial=payload.is_trial,
        enabled=payload.enabled,
        is_visible=payload.is_visible,
        sort_order=payload.sort_order,
        inbound_links=[
            TariffInbound(
                server_id=link.server_id,
                inbound_id=link.inbound_id,
                inbound_remark=link.inbound_remark,
                protocol=link.protocol,
            )
            for link in payload.inbound_links
        ],
        prices=_price_models(
            payload.prices,
            fallback_amount=payload.price,
            fallback_currency=payload.currency,
        ),
    )
    session.add(tariff)
    await session.commit()
    return _tariff_read(await _get_tariff(session, tariff.id))


@router.patch("/{tariff_id}", response_model=TariffRead)
async def update_tariff(
    tariff_id: int,
    payload: TariffUpdate,
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> TariffRead:
    tariff = await _get_tariff(session, tariff_id)
    data = payload.model_dump(exclude_unset=True)
    for field in (
        "name",
        "description",
        "duration_days",
        "traffic_limit_gb",
        "device_limit",
        "price",
        "currency",
        "is_trial",
        "enabled",
        "is_visible",
        "sort_order",
    ):
        if field in data:
            setattr(tariff, field, data[field].upper() if field == "currency" else data[field])
    if payload.inbound_links is not None:
        await _validate_servers(session, [link.server_id for link in payload.inbound_links])
        tariff.inbound_links = [
            TariffInbound(
                server_id=link.server_id,
                inbound_id=link.inbound_id,
                inbound_remark=link.inbound_remark,
                protocol=link.protocol,
            )
            for link in payload.inbound_links
        ]
    if payload.prices is not None:
        tariff.prices = _price_models(
            payload.prices,
            fallback_amount=tariff.price,
            fallback_currency=tariff.currency,
        )
    await session.commit()
    return _tariff_read(await _get_tariff(session, tariff.id))


async def _get_tariff(session: AsyncSession, tariff_id: int) -> Tariff:
    result = await session.execute(
        select(Tariff)
        .options(selectinload(Tariff.inbound_links), selectinload(Tariff.prices))
        .where(Tariff.id == tariff_id)
    )
    tariff = result.scalar_one_or_none()
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден.")
    return tariff


def _price_models(
    prices: list[TariffPriceCreate], *, fallback_amount: Decimal, fallback_currency: str
) -> list[TariffPrice]:
    effective_prices = prices or [
        TariffPriceCreate(
            payment_method=PaymentProviderType.MANUAL,
            amount=fallback_amount,
            currency=fallback_currency,
            enabled=True,
        )
    ]
    return [
        TariffPrice(
            payment_method=price.payment_method.value,
            amount=price.amount,
            currency=price.currency.upper(),
            enabled=price.enabled,
        )
        for price in effective_prices
    ]


def _tariff_read(tariff: Tariff) -> TariffRead:
    return TariffRead.model_validate(
        {
            "id": tariff.id,
            "name": tariff.name,
            "description": tariff.description,
            "duration_days": tariff.duration_days,
            "traffic_limit_gb": tariff.traffic_limit_gb,
            "device_limit": tariff.device_limit,
            "price": tariff.price,
            "currency": tariff.currency,
            "is_trial": tariff.is_trial,
            "enabled": tariff.enabled,
            "is_visible": tariff.is_visible,
            "sort_order": tariff.sort_order,
            "inbound_links": tariff.inbound_links,
            "prices": [
                {
                    "id": price.id,
                    "payment_method": _normal_payment_method(price.payment_method),
                    "amount": price.amount,
                    "currency": price.currency,
                    "enabled": price.enabled,
                }
                for price in tariff.prices
            ],
            "created_at": tariff.created_at,
            "updated_at": tariff.updated_at,
        }
    )


def _normal_payment_method(value: str | PaymentProviderType | None) -> str | None:
    if value is None:
        return None
    raw = value.value if isinstance(value, PaymentProviderType) else str(value)
    lowered = raw.lower()
    enum_value = PaymentProviderType.__members__.get(raw.upper())
    return enum_value.value if enum_value else lowered


async def _validate_servers(session: AsyncSession, server_ids: list[int]) -> None:
    unique_ids = set(server_ids)
    if not unique_ids:
        return
    result = await session.execute(select(Server.id).where(Server.id.in_(unique_ids)))
    found_ids = set(result.scalars())
    missing_ids = unique_ids - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не найдены серверы: {', '.join(str(value) for value in sorted(missing_ids))}.",
        )
