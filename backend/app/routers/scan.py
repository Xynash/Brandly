import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency
from app.routers.clients import _get_client
from app.schemas.scan import ScanIn, ScanOut, ViolationOut
from app.services.compliance import scan_text

router = APIRouter(prefix="/clients", tags=["scan"])


@router.post("/{client_id}/scan", response_model=ScanOut)
def scan(
    client_id: uuid.UUID,
    payload: ScanIn,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Check any text against this client's banned words. Powers the standalone scanner page."""
    client = _get_client(db, agency, client_id)
    words = client.hub.banned_words if client.hub else []
    result = scan_text(payload.text, [(w.word, w.severity) for w in words])
    return ScanOut(
        passed=result.passed,
        score=result.score,
        violations=[ViolationOut(**v.__dict__) for v in result.violations],
    )
