from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import PaymentProviderType
from app.db.models.tariff import Tariff
from app.schemas.commerce import TariffCatalogItem


class TariffCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_visible_tariffs(
        self, payment_method: PaymentProviderType | str | None = None
    ) -> list[TariffCatalogItem]:
        result = await self.session.execute(
            select(Tariff)
            .options(selectinload(Tariff.prices))
            .where(Tariff.enabled.is_(True), Tariff.is_visible.is_(True))
            .order_by(Tariff.sort_order, Tariff.id)
        )
        return [
            self._item(tariff, _method_value(payment_method))
            for tariff in result.scalars().unique()
        ]

    def _item(self, tariff: Tariff, payment_method: str | None) -> TariffCatalogItem:
        method_prices = {
            _method_value(price.payment_method) or "": {
                "amount": Decimal(price.amount),
                "currency": price.currency.upper(),
            }
            for price in tariff.prices
            if price.enabled
        }
        selected = method_prices.get(payment_method or "")
        price = Decimal(str(selected["amount"])) if selected else Decimal(tariff.price)
        currency = str(selected["currency"]) if selected else tariff.currency.upper()
        return TariffCatalogItem(
            id=tariff.id,
            name=tariff.name,
            description=tariff.description,
            duration_days=tariff.duration_days,
            traffic_limit_gb=tariff.traffic_limit_gb,
            device_limit=tariff.device_limit,
            is_trial=tariff.is_trial,
            price=price,
            currency=currency,
            payment_method_prices=method_prices,
            available_payment_methods=[key for key in method_prices if key],
        )


def select_tariff_price(
    tariff: Tariff, payment_method: PaymentProviderType | str
) -> tuple[Decimal, str]:
    method = _method_value(payment_method)
    tariff_price = next(
        (
            price
            for price in tariff.prices
            if _method_value(price.payment_method) == method and price.enabled
        ),
        None,
    )
    if tariff_price:
        return Decimal(tariff_price.amount), tariff_price.currency.upper()
    return Decimal(tariff.price), tariff.currency.upper()


def _method_value(value: PaymentProviderType | str | None) -> str | None:
    if value is None:
        return None
    return value.value if isinstance(value, PaymentProviderType) else str(value).lower()
