from pydantic import BaseModel
import uuid
from datetime import datetime


class AddContributorModel(BaseModel):
    contributor_id: uuid.UUID


class ListContributor(BaseModel):
    contributor_id: uuid.UUID
    revoked_at: datetime
