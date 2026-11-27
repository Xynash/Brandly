import uuid

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tenant import ProviderKey


class KeyConfigurationError(ValueError):
    pass


def key_cipher() -> Fernet:
    try:
        return Fernet(settings.provider_key_encryption_key.encode("ascii"))
    except ValueError as exc:
        raise KeyConfigurationError("Provider key encryption is unavailable") from exc


def load_key(db: Session, agency_id: uuid.UUID) -> str | None:
    if settings.llm_provider == "mock":
        return None
    stored = db.get(ProviderKey, (agency_id, settings.llm_provider))
    if stored is None:
        return None
    try:
        return key_cipher().decrypt(stored.encrypted_key.encode("ascii")).decode("ascii")
    except InvalidToken as exc:
        raise KeyConfigurationError("Could not open the configured provider key") from exc
