import uuid

from pydantic import BaseModel, Field, model_validator

from app.schemas.scan import ViolationOut


class GenerateIn(BaseModel):
    task: str | None = Field(default=None, min_length=1, max_length=4000)
    template_id: uuid.UUID | None = None
    values: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check(self):
        if (self.task is None) == (self.template_id is None):
            raise ValueError("Provide exactly one of 'task' or 'template_id'")
        if len(self.values) > 30 or any(len(v) > 1000 for v in self.values.values()):
            raise ValueError("Too many values, or a value is longer than 1000 characters")
        return self


class GenerateOut(BaseModel):
    text: str
    passed: bool
    flagged: bool  # True means still non-compliant after the retry; needs human review
    attempts: int
    score: int
    violations: list[ViolationOut]
