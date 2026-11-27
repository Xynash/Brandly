import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import Agency
from app.models.tenant import AuthSession
from app.services.auth import token_hash

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Actor:
    agency: Agency
    role: str
    user_id: uuid.UUID | None = None


def unauthorized(detail: str = "Invalid or expired access token") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def get_auth_session(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: Session = Depends(get_db),
) -> AuthSession:
    if credentials is None or not re.fullmatch(r"[A-Za-z0-9_-]{43}", credentials.credentials):
        raise unauthorized()
    session = db.get(AuthSession, token_hash(credentials.credentials))
    if session is None or session.expires_at <= datetime.now(UTC):
        raise unauthorized()
    return session


def get_actor(
    x_agency_id: uuid.UUID | None = Header(None),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: Session = Depends(get_db),
) -> Actor:
    if settings.auth_mode == "development":
        if x_agency_id is None:
            raise HTTPException(422, "X-Agency-Id header required in development mode")
        agency = db.get(Agency, x_agency_id)
        if agency is None:
            raise HTTPException(404, "Agency not found")
        return Actor(agency, "admin")

    user = get_auth_session(credentials, db).user
    if x_agency_id is not None and x_agency_id != user.agency_id:
        raise HTTPException(403, "Agency membership required")
    return Actor(user.agency, user.role, user.id)


def get_agency(actor: Actor = Depends(get_actor)) -> Agency:
    return actor.agency


def require_admin(actor: Actor = Depends(get_actor)) -> None:
    if actor.role != "admin":
        raise HTTPException(403, "Agency admin required")
