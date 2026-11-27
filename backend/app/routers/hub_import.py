import uuid

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency, require_admin
from app.models import Agency
from app.routers.clients import _get_client
from app.routers.generate import _rate_limit
from app.schemas.brand import HubUpdate
from app.services.hub_import import HubImportError, draft_hub, read_page
from app.services.llm import LLMError, get_provider
from app.services.provider_keys import KeyConfigurationError, load_key

router = APIRouter(prefix="/clients", tags=["hub import"])


class ImportIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


@router.post(
    "/{client_id}/hub/import", response_model=HubUpdate,
    dependencies=[Depends(require_admin), Depends(_rate_limit)],
)
def import_hub(
    client_id: uuid.UUID,
    payload: ImportIn,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """Return a draft. Save it through the normal hub update after review."""
    _get_client(db, agency, client_id)
    try:
        api_key = load_key(db, agency.id)
    except KeyConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    db.close()
    try:
        page = anyio.from_thread.run(read_page, payload.url)
        return draft_hub(get_provider(api_key) if api_key else get_provider(), page)
    except HubImportError as exc:
        raise HTTPException(422, str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(502, "Could not draft a brand hub") from exc
