import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.core.contributions.schemas import ListContributor
from src.core.versions.schemas import VersionRead


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: str
    updated_at: datetime


class DocumentCreateRequest(BaseModel):
    title: str


class DocumentRenameRequest(BaseModel):
    title: str


class DocumentReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    versions: list[VersionRead]
    contributions: list[ListContributor] = Field(default_factory=list)
