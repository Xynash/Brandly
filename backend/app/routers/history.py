import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency, Generation
from app.schemas.history import GenerationOut

router = APIRouter(prefix="/generations", tags=["history"])


@router.get("", response_model=list[GenerationOut])
def list_generations(
    client_id: uuid.UUID | None = None,
    flagged: bool | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Saved generations, newest first. Use flagged=true as the review queue for human checks."""
    stmt = select(Generation).where(Generation.agency_id == agency.id)
    if client_id is not None:
        stmt = stmt.where(Generation.client_id == client_id)
    if flagged is not None:
        stmt = stmt.where(Generation.flagged == flagged)
    stmt = stmt.order_by(Generation.created_at.desc(), Generation.id.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{generation_id}", response_model=GenerationOut)
def get_generation(
    generation_id: uuid.UUID,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    generation = db.scalar(
        select(Generation).where(Generation.id == generation_id, Generation.agency_id == agency.id)
    )
    if generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    return generation
