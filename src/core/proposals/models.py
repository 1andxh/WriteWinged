import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime
from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
from enum import Enum
from datetime import datetime, timezone


class ProposalStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
