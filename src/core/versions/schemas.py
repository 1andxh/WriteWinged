from pydantic import BaseModel
import uuid
from datetime import datetime


class VersionCreate(BaseModel):
    content: str


class VersionCreateResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    author_id: uuid.UUID
    document_id: uuid.UUID

    class Config:
        from_attributes = True


class VersionPublishRequest(BaseModel):
    version_id: uuid.UUID


class VersionRead(BaseModel):
    id: uuid.UUID
    content: str
    author_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
