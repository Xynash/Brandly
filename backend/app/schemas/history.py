import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.scan import ViolationOut


class GenerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    template_id: uuid.UUID | None
    task: str
    output: str
    passed: bool
    flagged: bool
    attempts: int
    score: int
    violations: list[ViolationOut]
    created_at: datetime
