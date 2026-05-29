from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.enums import PaymentProviderType
from app.schemas.commerce import TariffCatalogItem
from app.services.tariffs import TariffCatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/tariffs", response_model=list[TariffCatalogItem])
async def visible_tariffs(
    payment_method: PaymentProviderType | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[TariffCatalogItem]:
    return await TariffCatalogService(session).get_visible_tariffs(payment_method)
