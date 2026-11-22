import uuid

from pydantic import BaseModel, ConfigDict, Field


class AgencyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AgencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    industry: str | None


class BannedWordIn(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    severity: str = Field(default="block", pattern="^(block|warn)$")


class BannedWordOut(BannedWordIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class HubUpdate(BaseModel):
    tone_description: str = Field(default="", max_length=2000)
    audience: str = Field(default="", max_length=2000)
    dos: str = Field(default="", max_length=3000)
    donts: str = Field(default="", max_length=3000)
    sample_content: str = Field(default="", max_length=10000)
    banned_words: list[BannedWordIn] = Field(default_factory=list, max_length=200)


class HubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    tone_description: str
    audience: str
    dos: str
    donts: str
    sample_content: str
    banned_words: list[BannedWordOut]

