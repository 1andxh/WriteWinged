from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime


class AddContributorModel(BaseModel):
    contributor_id: uuid.UUID


class ListContributor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contributor_id: uuid.UUID
    revoked_at: datetime | None
