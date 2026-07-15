from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..db.dependency import session
from ..exceptions import InvalidCredentialsException, UserAlreadyExistsException
from .dependencies import get_current_user
from .models import User
from .schemas import TokenResponse, UserCreateModel, UserLogin, UserResponse
from .service import UserService
from .utils import get_access_token, verify_password


auth_router = APIRouter()
user_service = UserService()
current_user = Annotated[User, Depends(get_current_user)]


@auth_router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user_account(user: UserCreateModel, session: session):
    user_exists = await user_service.check_user_exists(user.email, session)
    if user_exists:
        raise UserAlreadyExistsException(user.email)

    return await user_service.create_user(user, session)


@auth_router.post("/login", response_model=TokenResponse)
async def login(login: UserLogin, session: session):
    user = await user_service.get_user_by_email(login.email, session)
    if user is None or user.password_hash is None:
        raise InvalidCredentialsException()

    if not verify_password(login.password, user.password_hash):
        raise InvalidCredentialsException()

    access_token = get_access_token(user)
    return JSONResponse(
        content={"token_type": "bearer", "access_token": access_token},
        status_code=status.HTTP_200_OK,
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_user(user: current_user):
    return user
