from app.core.config import Settings
from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong", password_hash)


def test_access_token_roundtrip() -> None:
    settings = Settings(jwt_secret_key="test-secret-with-at-least-thirty-two-bytes")
    token = create_access_token(subject="42", settings=settings)

    assert decode_token(token, expected_type="access", settings=settings)["sub"] == "42"
