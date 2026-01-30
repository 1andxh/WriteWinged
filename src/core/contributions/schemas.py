from pydantic import BaseModel
import uuid
from datetime import datetime


class AddContributorModel(BaseModel):
    contributor_id: uuid.UUID


class Contributors(BaseModel):
    contributor_id: uuid.UUID
    revoked_at: datetime
