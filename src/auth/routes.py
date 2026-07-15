from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from .dependencies import auth_service, get_current_user, token_service
from .models import User
from .schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreateModel,
    UserLogin,
    UserResponse,
)

auth_router = APIRouter()
current_user = Annotated[User, Depends(get_current_user)]


@auth_router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user_account(payload: UserCreateModel, auth_service: auth_service):
    return await auth_service.register(payload)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    request: Request,
    auth_service: auth_service,
    token_service: token_service,
):
    user = await auth_service.authenticate(payload.email, payload.password)
    tokens = await token_service.issue_token_pair(
        user,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(
        token_type="bearer",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, token_service: token_service):
    tokens = await token_service.refresh_tokens(payload.refresh_token)
    return TokenResponse(
        token_type="bearer",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshTokenRequest, token_service: token_service) -> None:
    await token_service.logout(payload.refresh_token)


@auth_router.get("/me", response_model=UserResponse)
async def get_user(user: current_user):
    return user
