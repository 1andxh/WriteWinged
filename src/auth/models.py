import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String
from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid
from enum import Enum
from pydantic import EmailStr, SecretStr
from typing import Optional


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    # redundant -- user with google_sub already shows auth provider


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__: str = "users"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    )
    email: EmailStr = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )
    username: str = Field(sa_column=Column(String(128), unique=True, nullable=False))
    google_sub: str = Field(
        sa_column=Column(String(255), unique=True, nullable=True, index=True)
    )
    password_hash: str = Field(sa_column=Column(String(255), nullable=True))
    bio: str = Field(sa_column=Column(String(255), nullable=True))
    role: UserRole = Field(
        sa_column=Column(
            SAEnum(UserRole, name="role_enum", native_enum=False),
            server_default=None,
            nullable=False,
        )
    )
    is_verified: bool = Field(default=False)
    last_login: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
