from pydantic import BaseModel
from typing import List


class EmailValidator(BaseModel):
    address: List[str]
