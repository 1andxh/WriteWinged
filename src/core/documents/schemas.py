from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from src.core.versions.schemas import VersionRead
from src.core.contributions.schemas import ListContributor


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
    contributors: list[ListContributor] = Field(default_factory=list)
