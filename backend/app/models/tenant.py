import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="agency", cascade="all, delete-orphan")
    clients: Mapped[list["Client"]] = relationship(back_populates="agency", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="writer")  # admin | writer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="users")


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("agency_id", "name", name="uq_client_agency_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="clients")
    hub: Mapped["BrandHub | None"] = relationship(
        back_populates="client", uselist=False, cascade="all, delete-orphan"
    )


class ProviderKey(Base):
    __tablename__ = "provider_keys"

    agency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="CASCADE"), primary_key=True,
    )
    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    encrypted_key: Mapped[str] = mapped_column(Text)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user: Mapped[User] = relationship()
