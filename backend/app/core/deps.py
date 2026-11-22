import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Agency


def get_agency(x_agency_id: uuid.UUID = Header(...), db: Session = Depends(get_db)) -> Agency:
    """Temporary stand-in for auth: the agency comes from the X-Agency-Id header."""
    agency = db.get(Agency, x_agency_id)
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found")
    return agency
