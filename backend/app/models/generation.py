import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Generation(Base):
    """One saved result of /generate: what was asked, what came back, and how it scored."""

    __tablename__ = "generations"
    __table_args__ = (Index("ix_generations_agency_created", "agency_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"))
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
    task: Mapped[str] = mapped_column(Text)  # the final task text (template already filled in)
    output: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean)
    flagged: Mapped[bool] = mapped_column(Boolean, index=True)  # still non-compliant after the retry
    attempts: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    violations: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
