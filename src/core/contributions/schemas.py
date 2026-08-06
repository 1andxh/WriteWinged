import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AddContributorModel(BaseModel):
    contributor_id: uuid.UUID


class ListContributor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contributor_id: uuid.UUID
    revoked_at: datetime | None
