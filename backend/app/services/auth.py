import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import User
from app.models.tenant import AuthSession

SESSION_DURATION = timedelta(hours=24)


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**15, r=8, p=3,
        maxmem=48 * 1024 * 1024, dklen=32,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt-v1${salt.hex()}${_derive(password, salt).hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if encoded is None:
        _derive(password, bytes(16))  # Equal work for an unknown account.
        return False
    try:
        version, salt, digest = encoded.split("$")
        if version != "scrypt-v1":
            return False
        return hmac.compare_digest(_derive(password, bytes.fromhex(salt)), bytes.fromhex(digest))
    except ValueError:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def new_session(db: Session, user: User) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    expires_at = now + SESSION_DURATION
    db.add(AuthSession(token_hash=token_hash(token), user=user, expires_at=expires_at))
    return token, expires_at
