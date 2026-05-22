from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import AuthenticationError

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    return hash_password(token)


def verify_token_hash(token: str, token_hash: str) -> bool:
    return verify_password(token, token_hash)


def create_access_token(*, subject: str, settings: Settings) -> str:
    return _encode_token(
        subject=subject,
        token_type="access",
        ttl=timedelta(minutes=settings.access_token_ttl_minutes),
        settings=settings,
    )


def create_refresh_token(*, subject: str, settings: Settings) -> tuple[str, str]:
    jti = str(uuid4())
    token = _encode_token(
        subject=subject,
        token_type="refresh",
        ttl=timedelta(days=settings.refresh_token_ttl_days),
        settings=settings,
        jti=jti,
    )
    return token, jti


def decode_token(token: str, *, expected_type: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token is invalid or expired.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError("Token type is invalid.")
    if not payload.get("sub"):
        raise AuthenticationError("Token subject is missing.")
    return payload


def _encode_token(
    *,
    subject: str,
    token_type: str,
    ttl: timedelta,
    settings: Settings,
    jti: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    if jti:
        payload["jti"] = jti
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
