from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_auth_session, unauthorized
from app.models import Agency, User
from app.models.tenant import AuthSession
from app.services.auth import hash_password, new_session, verify_password
from app.services.ratelimit import SlidingWindowLimiter

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limiter = SlidingWindowLimiter()
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=320, pattern=r"^[^\s@\x00]+@[^\s@\x00]+\.[^\s@\x00]+$"),
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\x00]+$")]


class LoginIn(BaseModel):
    email: Email
    password: SecretStr = Field(min_length=1, max_length=256)


class SignupIn(LoginIn):
    password: SecretStr = Field(min_length=15, max_length=256)
    full_name: Name
    agency_name: Name


class SessionOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    wait = auth_limiter.hit(f"ip:{ip}", 15) or auth_limiter.hit("global", 120)
    if wait is not None:
        raise HTTPException(429, "Too many authentication attempts", headers={"Retry-After": str(wait)})


def _find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email))


def _issue_session(db: Session, user: User, response: Response) -> SessionOut:
    token, expires_at = new_session(db, user)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return SessionOut(access_token=token, expires_at=expires_at)


@router.post("/signup", response_model=SessionOut, status_code=201, dependencies=[Depends(_rate_limit)])
def signup(payload: SignupIn, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    password_hash = hash_password(payload.password.get_secret_value())
    if _find_user(db, email) is not None:
        raise HTTPException(409, "An account already uses this email")
    user = User(
        email=email, full_name=payload.full_name, role="admin", password_hash=password_hash,
        agency=Agency(name=payload.agency_name),
    )
    db.add(user)
    try:
        db.flush()
        return _issue_session(db, user, response)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "An account already uses this email") from exc


@router.post("/login", response_model=SessionOut, dependencies=[Depends(_rate_limit)])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = _find_user(db, payload.email.lower())
    if not verify_password(payload.password.get_secret_value(), user.password_hash if user else None):
        raise unauthorized("Invalid email or password")
    return _issue_session(db, user, response)


@router.post("/logout", status_code=204, response_class=Response)
def logout(session: AuthSession = Depends(get_auth_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    return Response(status_code=204)
