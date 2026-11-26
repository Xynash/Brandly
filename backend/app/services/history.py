import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError

from app.models import Generation
from app.services.generation import GenerationResult

logger = logging.getLogger("brandly")


def save_generation(
    db,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    template_id: uuid.UUID | None,
    task: str,
    result: GenerationResult,
) -> uuid.UUID | None:
    """Store one generation and return its id.

    Never raises: if the save fails, the writer still gets the draft they waited for."""
    generation = Generation(
        agency_id=agency_id,
        client_id=client_id,
        template_id=template_id,
        task=task,
        output=result.text,
        passed=result.scan.passed,
        flagged=result.flagged,
        attempts=result.attempts,
        score=result.scan.score,
        violations=[v.__dict__ for v in result.scan.violations],
    )
    try:
        db.add(generation)
        db.commit()
        return generation.id
    except SQLAlchemyError:
        db.rollback()
        logger.exception("could not save generation for client %s", client_id)
        return None
