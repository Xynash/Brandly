import uuid

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    client_id: uuid.UUID | None = None


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    body: str
    client_id: uuid.UUID | None
    variables: list[str]
