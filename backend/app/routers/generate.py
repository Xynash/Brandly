import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency
from app.routers.clients import _get_client
from app.schemas.generate import GenerateIn, GenerateOut
from app.schemas.scan import ViolationOut
from app.services.context import build_context
from app.services.generation import generate_checked
from app.services.llm import LLMError, get_provider

router = APIRouter(prefix="/clients", tags=["generate"])


@router.post("/{client_id}/generate", response_model=GenerateOut)
def generate(
    client_id: uuid.UUID,
    payload: GenerateIn,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Build the client's prompt, call the model, scan the draft, retry once if needed."""
    client = _get_client(db, agency, client_id)
    ctx, banned = build_context(client)
    try:
        result = generate_checked(get_provider(), ctx, payload.task, banned)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return GenerateOut(
        text=result.text,
        passed=result.scan.passed,
        flagged=result.flagged,
        attempts=result.attempts,
        score=result.scan.score,
        violations=[ViolationOut(**v.__dict__) for v in result.scan.violations],
    )
