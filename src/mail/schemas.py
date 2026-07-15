from typing import List

from pydantic import BaseModel


class EmailValidator(BaseModel):
    addresses: List[str]
