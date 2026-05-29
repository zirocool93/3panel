from decimal import Decimal

from app.schemas.commerce import TariffCatalogItem


def tariff_card(tariff: TariffCatalogItem) -> str:
    traffic = "безлимит" if tariff.traffic_limit_gb is None else f"{tariff.traffic_limit_gb} ГБ"
    devices = "без ограничений" if tariff.device_limit is None else str(tariff.device_limit)
    methods = ", ".join(tariff.available_payment_methods) or "базовая цена"
    description = f"\n{tariff.description}\n" if tariff.description else "\n"
    return (
        f"<b>{tariff.name}</b>"
        f"{description}"
        f"Срок: {tariff.duration_days} дн.\n"
        f"Устройств: {devices}\n"
        f"Трафик: {traffic}\n"
        f"Цена: {format_money(tariff.price)} {tariff.currency}\n"
        f"Способы оплаты: {methods}"
    )


def format_money(value: Decimal) -> str:
    normalized = value.quantize(Decimal("1")) if value == value.to_integral() else value
    return str(normalized)
