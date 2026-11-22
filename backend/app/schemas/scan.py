from pydantic import BaseModel, Field


class ScanIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class ViolationOut(BaseModel):
    word: str
    severity: str
    start: int
    end: int
    matched: str


class ScanOut(BaseModel):
    passed: bool
    score: int
    violations: list[ViolationOut]
