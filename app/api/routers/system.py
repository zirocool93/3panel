from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_admin, settings_dep
from app.core.config import Settings
from app.core.enums import AdminRole
from app.db.models.admin import AdminUser
from app.schemas.system import AdminUpdateStatus
from app.services.system.updates import (
    AdminUpdateBusy,
    AdminUpdateDisabled,
    AdminUpdateError,
    admin_update_manager,
)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/updates", response_model=AdminUpdateStatus)
async def get_update_status(
    admin: AdminUser = Depends(get_current_admin),
    settings: Settings = Depends(settings_dep),
) -> AdminUpdateStatus:
    _require_owner(admin)
    return AdminUpdateStatus.model_validate(admin_update_manager.status(settings).__dict__)


@router.post(
    "/updates",
    response_model=AdminUpdateStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_update(
    admin: AdminUser = Depends(get_current_admin),
    settings: Settings = Depends(settings_dep),
) -> AdminUpdateStatus:
    _require_owner(admin)
    try:
        update_state = admin_update_manager.start(settings)
    except AdminUpdateDisabled as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AdminUpdateBusy as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AdminUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return AdminUpdateStatus.model_validate(update_state.__dict__)


def _require_owner(admin: AdminUser) -> None:
    if admin.role != AdminRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can trigger deployment updates.",
        )
