from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Agency
from app.schemas.brand import AgencyCreate, AgencyOut

router = APIRouter(prefix="/agencies", tags=["agencies"])


@router.post("", response_model=AgencyOut, status_code=201)
def create_agency(payload: AgencyCreate, db: Session = Depends(get_db)):
    """Dev-only bootstrap. Replaced by real signup once auth is added."""
    agency = Agency(name=payload.name.strip())
    db.add(agency)
    db.commit()
    return agency
