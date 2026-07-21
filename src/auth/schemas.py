import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: uuid.UUID
    sid: uuid.UUID
    type: str
    exp: int
    iat: int
    jti: str


class GoogleUser(BaseModel):
    sub: str
    email: str
    name: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    new_password: str = Field(min_length=8, max_length=255)
    confirm_new_password: str

    @model_validator(mode="after")
    def _passwords_match(self) -> "PasswordResetConfirm":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class MessageResponse(BaseModel):
    message: str
