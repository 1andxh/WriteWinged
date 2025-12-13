from fastapi import APIRouter, Request, status, Depends
from authlib.integrations.starlette_client import OAuthError
from fastapi.security import OAuth2PasswordRequestForm
from .utils import oauth
from ..db.dependency import session
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from .schemas import GoogleUser, TokenResponse, UserLogin, UserCreateModel, UserResponse
from .service import GoogleUserService, UserService
from .dependencies import AccessTokenBearer, RefreshTokenBearer
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from .utils import create_access_token, verify_password, get_tokens
from datetime import timedelta, datetime
from .models import User
from typing import Annotated
from ..db.redis import add_token_to_blocklist
import pprint

GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/api/auth/callback/google"

auth_router = APIRouter()
google_user_service = GoogleUserService()
user_service = UserService()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()


"""OAuth-Google"""


@auth_router.get("/google", name="google_login")
async def login_via_google(request: Request):
    # url = request.url_for(GOOGLE_REDIRECT_URI)
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)  # type: ignore


@auth_router.get(
    "/callback/google", name="google_callback", response_model=TokenResponse
)
async def auth_via_google(request: Request, session: session):
    try:
        token = await oauth.google.authorize_access_token(request)  # type: ignore
    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user = token.get("userinfo")

    print(user)

    google_user = GoogleUser(**user)

    is_existing_user = await google_user_service.get_user_by_google_sub(
        google_user.sub, session
    )

    if is_existing_user:
        user = is_existing_user
    else:
        user = await google_user_service.create_user_from_google_info(
            google_user, session, is_verified=True
        )
    # todo: change is_verified at this point
    if user is not None:
        access_token, refresh_token = get_tokens(user)
        return JSONResponse(
            content={
                "token": "bearer",
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            status_code=status.HTTP_200_OK,
        )

    # return RedirectResponse(
    #     f"{FRONTEND_URL}/auth?access_token={access_token}&refresh_token={refresh_token}"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="something went wrong"
    )


# local auth


@auth_router.post("/login")
async def login(login: UserLogin, session: session):
    user = await user_service.get_user_by_email(login.email, session)
    if user is not None:
        is_valid_password = verify_password(login.password, user.password_hash)
        if is_valid_password:
            access_token, refresh_token = get_tokens(user)

            return JSONResponse(
                content={
                    "message": "login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
        )


@auth_router.post(
    "/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def create_user_account(user: UserCreateModel, session: session):
    user_exists = await user_service.check_user_exists(user.email, session)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    new_user = await user_service.create_user(user, session)
    return new_user


@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def revoke_token(token_data: dict = Depends(access_token_bearer)):
    jti = token_data["jti"]
    await add_token_to_blocklist(jti)
    return {"message": "Logged out successfully"}


@auth_router.post("/refresh")
async def refresh_token(token_data: dict = Depends(refresh_token_bearer)):
    expiry = token_data["exp"]
    if datetime.fromtimestamp(expiry) > datetime.now():
        access_token = create_access_token(data=token_data["user"])
        return JSONResponse(content={"access_token": access_token})
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired retoken"
    )
