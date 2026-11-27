import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency, require_admin
from app.models import Agency, BannedWord, BrandHub, Client
from app.schemas.brand import ClientCreate, ClientOut, HubOut, HubUpdate

from app.services.presets import CATALOG

router = APIRouter(prefix="/clients", tags=["clients"])


def _get_client(db: Session, agency: Agency, client_id: uuid.UUID) -> Client:
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.agency_id == agency.id)
    )
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("", response_model=ClientOut, status_code=201, dependencies=[Depends(require_admin)])
def create_client(
    payload: ClientCreate,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    client = Client(agency_id=agency.id, name=payload.name.strip(), industry=payload.industry)
    client.hub = BrandHub()  # every client starts with an empty hub
    db.add(client)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A client with this name already exists")
    return client


@router.get("", response_model=list[ClientOut])
def list_clients(agency: Agency = Depends(get_agency), db: Session = Depends(get_db)):
    return db.scalars(
        select(Client).where(Client.agency_id == agency.id).order_by(Client.name)
    ).all()


@router.delete("/{client_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_client(
    client_id: uuid.UUID,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    db.delete(_get_client(db, agency, client_id))
    db.commit()
    return Response(status_code=204)


@router.get("/{client_id}/hub", response_model=HubOut)
def get_hub(
    client_id: uuid.UUID,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    client = _get_client(db, agency, client_id)
    return HubOut.model_validate(client.hub)


@router.put("/{client_id}/hub", response_model=HubOut, dependencies=[Depends(require_admin)])
def update_hub(
    client_id: uuid.UUID,
    payload: HubUpdate,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    client = _get_client(db, agency, client_id)
    hub = client.hub
    if hub is None:
        hub = BrandHub()
        client.hub = hub

    if "preset_ids" in payload.model_fields_set:
        preset_ids = list(dict.fromkeys(payload.preset_ids))
        if any(preset_id not in CATALOG for preset_id in preset_ids):
            raise HTTPException(422, "Unknown compliance preset")
        hub.preset_ids = preset_ids
    hub.tone_description = payload.tone_description
    hub.audience = payload.audience
    hub.dos = payload.dos
    hub.donts = payload.donts
    hub.sample_content = payload.sample_content

    # Sync banned words by diffing, so unchanged words are never deleted and re-inserted
    incoming = {bw.word.strip().lower(): bw.severity for bw in payload.banned_words if bw.word.strip()}
    existing = {w.word: w for w in hub.banned_words}
    for word, row in existing.items():
        if word not in incoming:
            hub.banned_words.remove(row)
        else:
            row.severity = incoming[word]
    for word, severity in incoming.items():
        if word not in existing:
            hub.banned_words.append(BannedWord(word=word, severity=severity))

    db.commit()
    db.refresh(hub)
    return HubOut.model_validate(hub)
