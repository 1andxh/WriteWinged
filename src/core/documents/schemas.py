from pydantic import BaseModel
from datetime import datetime
import uuid


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

    class Config:
        from_attributes = True
