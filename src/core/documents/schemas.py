from pydantic import BaseModel
from datetime import datetime
import uuid
from src.core.versions.schemas import VersionRead
from src.core.contributions.schemas import ListContributor


class DocumentResponse(BaseModel):
    document_id: uuid.UUID
    state: str
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentCreateRequest(BaseModel):
    title: str


class DocumentRenameRequest(BaseModel):
    title: str


class DocumentReadResponse(BaseModel):
    id: uuid.UUID
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    versions: list[VersionRead]
    contributors: list[ListContributor]

    class Config:
        from_attributes = True
