from pydantic import BaseModel, Field

from app.schemas.scan import ViolationOut


class GenerateIn(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class GenerateOut(BaseModel):
    text: str
    passed: bool
    flagged: bool  # True means still non-compliant after the retry; needs human review
    attempts: int
    score: int
    violations: list[ViolationOut]
