from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditActorType, AuditEntityType
from app.db.models.billing import AuditLog


def add_audit_log(
    session: AsyncSession,
    *,
    action: str,
    entity_type: AuditEntityType,
    entity_id: int | str | None,
    actor_type: AuditActorType = AuditActorType.SYSTEM,
    actor_id: int | str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=before,
        after=after,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(UTC),
    )
    session.add(entry)
    return entry
