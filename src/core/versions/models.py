import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text
from sqlmodel import SQLModel, Field


class Version(SQLModel, table=True):
    __tablename__: str = "versions"
