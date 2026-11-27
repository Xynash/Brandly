from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency
from app.schemas.brand import AgencyCreate, AgencyOut

router = APIRouter(prefix="/agencies", tags=["agencies"])


@router.get("/current", response_model=AgencyOut)
def current_agency(agency: Agency = Depends(get_agency)):
    return agency


@router.post("", response_model=AgencyOut, status_code=201)
def create_agency(payload: AgencyCreate, db: Session = Depends(get_db)):
    if settings.auth_mode != "development":
        raise HTTPException(403, "Sign up through /auth/signup to create an agency")
    agency = Agency(name=payload.name.strip())
    db.add(agency)
    db.commit()
    return agency
