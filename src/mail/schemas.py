from pydantic import BaseModel
from typing import List


class EmailValidator(BaseModel):
    addresses: List[str]
