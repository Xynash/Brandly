import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency, Template
from app.routers.clients import _get_client
from app.schemas.generate import GenerateIn, GenerateOut
from app.schemas.scan import ViolationOut
from app.services.context import build_context
from app.services.generation import generate_checked
from app.services.llm import LLMError, get_provider
from app.services.templating import MissingVariables, render

router = APIRouter(prefix="/clients", tags=["generate"])


@router.post("/{client_id}/generate", response_model=GenerateOut)
def generate(
    client_id: uuid.UUID,
    payload: GenerateIn,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Build the client's prompt, call the model, scan the draft, retry once if needed.

    The task is either given directly, or rendered from a template plus the writer's values."""
    client = _get_client(db, agency, client_id)

    if payload.template_id is not None:
        template = db.scalar(
            select(Template).where(Template.id == payload.template_id, Template.agency_id == agency.id)
        )
        if template is None or (template.client_id is not None and template.client_id != client.id):
            raise HTTPException(status_code=404, detail="Template not found")
        try:
            task = render(template.body, payload.values)
        except MissingVariables as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    else:
        task = payload.task

    ctx, banned = build_context(client)
    try:
        result = generate_checked(get_provider(), ctx, task, banned)
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
