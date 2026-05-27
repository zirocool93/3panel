from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db
from app.api.routers.clients import transaction_read
from app.db.models.admin import AdminUser
from app.db.models.billing import BalanceTransaction
from app.schemas.clients import ClientTransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[ClientTransactionRead])
async def list_transactions(
    _admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> list[ClientTransactionRead]:
    result = await session.execute(
        select(BalanceTransaction)
        .options(selectinload(BalanceTransaction.user))
        .order_by(BalanceTransaction.id.desc())
        .limit(500)
    )
    return [transaction_read(transaction) for transaction in result.scalars()]
