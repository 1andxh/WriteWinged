import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VersionCreate(BaseModel):
    content: str


class VersionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    author_id: uuid.UUID
    document_id: uuid.UUID


class VersionPublishRequest(BaseModel):
    version_id: uuid.UUID


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    author_id: uuid.UUID
    created_at: datetime
