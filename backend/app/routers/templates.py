import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_agency
from app.models import Agency, Template
from app.routers.clients import _get_client
from app.schemas.template import TemplateCreate, TemplateOut
from app.services.templating import extract_variables

router = APIRouter(prefix="/templates", tags=["templates"])


def _out(t: Template) -> TemplateOut:
    return TemplateOut(
        id=t.id, name=t.name, body=t.body, client_id=t.client_id, variables=extract_variables(t.body)
    )


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(
    payload: TemplateCreate,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    if payload.client_id is not None:
        _get_client(db, agency, payload.client_id)  # 404 unless the client belongs to this agency
    t = Template(
        agency_id=agency.id, client_id=payload.client_id, name=payload.name.strip(), body=payload.body
    )
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A template with this name already exists")
    return _out(t)


@router.get("", response_model=list[TemplateOut])
def list_templates(
    client_id: uuid.UUID | None = None,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    """With client_id: agency-wide templates plus that client's own. Without: everything."""
    stmt = select(Template).where(Template.agency_id == agency.id)
    if client_id is not None:
        _get_client(db, agency, client_id)
        stmt = stmt.where(or_(Template.client_id.is_(None), Template.client_id == client_id))
    return [_out(t) for t in db.scalars(stmt.order_by(Template.name))]


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: uuid.UUID,
    agency: Agency = Depends(get_agency),
    db: Session = Depends(get_db),
):
    t = db.scalar(select(Template).where(Template.id == template_id, Template.agency_id == agency.id))
    if t is None:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
    return Response(status_code=204)
