from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class BlockedUserError(ValueError):
    pass


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_telegram_user(
        self,
        *,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        display_name: str | None = None,
        start_payload: str | None = None,
    ) -> User:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            await self.session.flush()

        if user.is_blocked:
            raise BlockedUserError("User is blocked.")

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.language_code = language_code
        user.display_name = display_name or _display_name(username, first_name, last_name)
        user.last_seen_at = datetime.now(UTC)
        if start_payload:
            user.start_payload = start_payload[:255]
            await self._apply_start_payload(user, start_payload)
        return user

    async def _apply_start_payload(self, user: User, payload: str) -> None:
        if payload.startswith("source_"):
            user.source = payload.removeprefix("source_")[:255]
            return
        if not payload.startswith("ref_") or user.referrer_id is not None:
            return
        ref_raw = payload.removeprefix("ref_")
        if not ref_raw.isdigit():
            return
        referrer_id = int(ref_raw)
        if referrer_id == user.id:
            return
        referrer = await self.session.get(User, referrer_id)
        if referrer:
            user.referrer_id = referrer.id


def _display_name(
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> str | None:
    name = " ".join(part for part in (first_name, last_name) if part)
    if name:
        return name
    return username
