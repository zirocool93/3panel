from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class CredentialEncryptionError(ValueError):
    pass


def generate_credentials_key() -> str:
    return Fernet.generate_key().decode("ascii")


def encrypt_secret(value: str | None, *, settings: Settings) -> str | None:
    if value is None or value == "":
        return None
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None, *, settings: Settings) -> str | None:
    if value is None or value == "":
        return None
    try:
        return _fernet(settings).decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        message = "Не удалось расшифровать сохранённые учётные данные."
        raise CredentialEncryptionError(message) from exc


def _fernet(settings: Settings) -> Fernet:
    key = settings.credentials_encryption_key.get_secret_value()
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError(
            "CREDENTIALS_ENCRYPTION_KEY должен быть Fernet-ключом. "
            "Сгенерируйте его командой: python -c \"from cryptography.fernet import "
            "Fernet; print(Fernet.generate_key().decode())\""
        ) from exc
