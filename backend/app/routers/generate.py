import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.core.deps import Actor, get_actor, get_agency
from app.models import Agency, Template
from app.routers.clients import _get_client
from app.schemas.generate import GenerateIn, GenerateOut
from app.schemas.scan import ViolationOut
from app.services.context import build_context
from app.services.generation import generate_checked
from app.services.history import save_generation
from app.services.llm import LLMError, get_provider
from app.services.provider_keys import KeyConfigurationError, load_key
from app.services.ratelimit import SlidingWindowLimiter
from app.services.templating import MissingVariables, render

router = APIRouter(prefix="/clients", tags=["generate"])

generate_limiter = SlidingWindowLimiter(window_seconds=60)


def _rate_limit(agency: Agency = Depends(get_agency)) -> None:
    """Protects the Gemini quota: each agency gets a fixed number of generations per minute."""
    wait = generate_limiter.hit(str(agency.id), settings.generate_rate_limit_per_minute)
    if wait is not None:
        raise HTTPException(
            status_code=429,
            detail=f"Too many generation requests. Try again in {wait} seconds.",
            headers={"Retry-After": str(wait)},
        )


def _prepare(
    client_id: uuid.UUID,
    payload: GenerateIn,
    agency: Agency,
    db: Session,
):
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
        api_key = load_key(db, agency.id)
    except KeyConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    return ctx, banned, task, api_key


def _generate(prepared, agency_id, client_id, template_id, user_id) -> GenerateOut:
    ctx, banned, task, api_key = prepared
    try:
        provider = get_provider(api_key) if api_key else get_provider()
        result = generate_checked(provider, ctx, task, banned)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    with SessionLocal() as db:
        generation_id = save_generation(
            db,
            agency_id=agency_id,
            client_id=client_id,
            template_id=template_id,
            task=task,
            result=result,
            user_id=user_id,
        )
    return GenerateOut(
        id=generation_id,
        text=None if result.flagged else result.text,
        passed=result.scan.passed,
        flagged=result.flagged,
        attempts=result.attempts,
        score=result.scan.score,
        violations=[ViolationOut(**v.__dict__) for v in result.scan.violations],
    )


@router.post("/{client_id}/generate", response_model=GenerateOut, dependencies=[Depends(_rate_limit)])
def generate(
    client_id: uuid.UUID,
    payload: GenerateIn,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    prepared = _prepare(client_id, payload, actor.agency, db)
    agency_id = actor.agency.id
    db.close()
    return _generate(prepared, agency_id, client_id, payload.template_id, actor.user_id)


@router.post(
    "/{client_id}/generate/stream",
    response_class=StreamingResponse,
    dependencies=[Depends(_rate_limit)],
    responses={200: {"content": {"text/event-stream": {}}}},
)
def stream_generation(
    client_id: uuid.UUID,
    payload: GenerateIn,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    prepared = _prepare(client_id, payload, actor.agency, db)
    agency_id = actor.agency.id
    db.close()

    def events():
        yield 'event: started\ndata: {}\n\n'
        try:
            result = _generate(prepared, agency_id, client_id, payload.template_id, actor.user_id)
        except HTTPException as exc:
            data = json.dumps({"status": exc.status_code, "detail": exc.detail})
            yield f"event: error\ndata: {data}\n\n"
            return
        if result.flagged:
            data = result.model_dump_json(exclude={"text", "violations"})
            yield f"event: review_required\ndata: {data}\n\n"
        else:
            yield f"event: completed\ndata: {result.model_dump_json()}\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
