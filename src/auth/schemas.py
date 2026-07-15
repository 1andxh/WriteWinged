from pydantic import BaseModel, ConfigDict, EmailStr, Field
import uuid


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    token_type: str
    access_token: str
