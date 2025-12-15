from fastapi import APIRouter, Request, status, Depends, BackgroundTasks
from authlib.integrations.starlette_client import OAuthError
from fastapi.security import OAuth2PasswordRequestForm

from src.mail.schemas import EmailValidator
from .utils import oauth
from ..db.dependency import session
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from .schemas import GoogleUser, TokenResponse, UserLogin, UserCreateModel, UserResponse
from .service import GoogleUserService, UserService
from .dependencies import AccessTokenBearer, RefreshTokenBearer, get_currrent_user
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from .utils import create_access_token, verify_password, get_tokens
from datetime import timedelta, datetime
from .models import User
from typing import Annotated, Any
from ..db.redis import add_token_to_blocklist
from ..mail.service import MailService
from ..mail.utils import decode_url_safe_token
from ..mail.mail import create_message, mail
from ..config import config
from .templates import templates
from datetime import datetime as dt
import pprint

GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/api/auth/callback/google"

auth_router = APIRouter()
google_user_service = GoogleUserService()
user_service = UserService()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()
mail_service = MailService(config)


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

    token = mail_service.create_email_verification_token(data={"email": user.email})
    link = f"https://{config.DOMAIN}/api/auth/verify/{token}"

    return new_user


@auth_router.get("/verify")
async def verify_user(token: str, session: session):
    pass


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


user = Annotated[dict[str, Any], Depends(get_currrent_user)]


@auth_router.get("/me", response_model=UserResponse)
async def get_user(user: user):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authentication credentials",
        )
    return user


# emails
@auth_router.post("/send-mail")
async def send_mail(emails: EmailValidator, bg_task: BackgroundTasks):
    recipients = emails.addresses
    template = templates.get_template("base.html")

    html_content = template.render({"year": dt.now().year})

    message = create_message(
        recepients=recipients,
        subject="Collaborative writing at the 'write' place",
        body=html_content,
    )
    bg_task.add_task(mail.send_message, message)
    return {"message": "Email sent successfully"}
