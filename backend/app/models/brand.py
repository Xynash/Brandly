import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class BrandHub(Base):
    __tablename__ = "brand_hubs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), unique=True
    )  # one hub per client
    tone_description: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(Text, default="")
    dos: Mapped[str] = mapped_column(Text, default="")
    donts: Mapped[str] = mapped_column(Text, default="")
    preset_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    sample_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="hub")
    banned_words: Mapped[list["BannedWord"]] = relationship(
        back_populates="hub", cascade="all, delete-orphan"
    )


class BannedWord(Base):
    __tablename__ = "banned_words"
    __table_args__ = (UniqueConstraint("hub_id", "word", name="uq_hub_word"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brand_hubs.id", ondelete="CASCADE"), index=True)
    word: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(10), default="block")  # block | warn

    hub: Mapped["BrandHub"] = relationship(back_populates="banned_words")
