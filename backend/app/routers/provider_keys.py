from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency, require_admin
from app.models import Agency
from app.models.tenant import ProviderKey
from app.services.provider_keys import KeyConfigurationError, key_cipher

router = APIRouter(
    prefix="/agencies/current/provider-keys", tags=["provider keys"],
    dependencies=[Depends(require_admin)],
)

Provider = Literal["gemini", "openai", "anthropic"]


class KeyIn(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    api_key: SecretStr = Field(min_length=1, max_length=2048)


@router.put("/{provider}", status_code=204, response_class=Response)
def put_key(provider: Provider, payload: KeyIn, agency: Agency = Depends(get_agency), db: Session = Depends(get_db)):
    key = payload.api_key.get_secret_value().strip()
    if not key or not key.isascii() or any(not 33 <= ord(char) <= 126 for char in key):
        raise HTTPException(422, "Invalid provider key format")
    try:
        encrypted = key_cipher().encrypt(key.encode("ascii")).decode("ascii")
    except KeyConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    query = insert(ProviderKey).values(agency_id=agency.id, provider=provider, encrypted_key=encrypted)
    db.execute(query.on_conflict_do_update(
        index_elements=[ProviderKey.agency_id, ProviderKey.provider],
        set_={"encrypted_key": query.excluded.encrypted_key},
    ))
    db.commit()
    return Response(status_code=204)


@router.delete("/{provider}", status_code=204, response_class=Response)
def delete_key(provider: Provider, agency: Agency = Depends(get_agency), db: Session = Depends(get_db)):
    stored = db.get(ProviderKey, (agency.id, provider))
    if stored is not None:
        db.delete(stored)
        db.commit()
    return Response(status_code=204)
