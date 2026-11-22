from pydantic import BaseModel, Field


class PromptPreviewIn(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class PromptPreviewOut(BaseModel):
    system: str
    user: str
