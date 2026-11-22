import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency
from app.routers.clients import _get_client
from app.schemas.prompt import PromptPreviewIn, PromptPreviewOut
from app.services.prompt_builder import HubContext, build_prompt

router = APIRouter(prefix="/clients", tags=["prompts"])


@router.post("/{client_id}/prompt-preview", response_model=PromptPreviewOut)
def prompt_preview(
    client_id: uuid.UUID,
    payload: PromptPreviewIn,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Shows the exact prompt that would be sent to the LLM. No model call is made."""
    client = _get_client(db, agency, client_id)
    hub = client.hub
    words = hub.banned_words if hub else []
    ctx = HubContext(
        client_name=client.name,
        industry=client.industry,
        tone_description=hub.tone_description if hub else "",
        audience=hub.audience if hub else "",
        dos=hub.dos if hub else "",
        donts=hub.donts if hub else "",
        sample_content=hub.sample_content if hub else "",
        banned_block=[w.word for w in words if w.severity == "block"],
        banned_warn=[w.word for w in words if w.severity == "warn"],
    )
    built = build_prompt(ctx, payload.task)
    return PromptPreviewOut(system=built.system, user=built.user)
