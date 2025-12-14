from pydantic import BaseModel, SecretStr, EmailStr, Field
import uuid
from datetime import datetime
from typing import List


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str
    is_verified: bool


class UserCreateModel(BaseModel):
    username: str
    email: EmailStr = Field(min_length=8)
    password: str = Field(min_length=8, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreateBio(BaseModel):
    bio: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_toke: str
    type: str


# OAuth Schema
class GoogleUser(BaseModel):
    sub: str
    email: str
    name: str

    class Config:
        from_attributes = True


class GoogleUserCreateModel(BaseModel):
    email: EmailStr
    google_sub: str
    username: str
    is_verified: bool
