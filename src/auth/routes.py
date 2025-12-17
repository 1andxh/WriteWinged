from fastapi import APIRouter, Request, status, Depends, BackgroundTasks
from authlib.integrations.starlette_client import OAuthError
from fastapi.security import OAuth2PasswordRequestForm
from src.mail.schemas import EmailValidator
from .utils import oauth, hash_password
from ..db.dependency import session
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from .schemas import (
    GoogleUser,
    TokenResponse,
    UserLogin,
    UserCreateModel,
    UserResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
)
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
from urllib.parse import quote
import pprint


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
    return await oauth.google.authorize_redirect(request, config.GOOGLE_REDIRECT_URI)  # type: ignore


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


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user: UserCreateModel, bg_task: BackgroundTasks, session: session
):
    user_exists = await user_service.check_user_exists(user.email, session)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    new_user = await user_service.create_user(user, session)

    # send mail to verify user
    token = mail_service.create_email_verification_token(data={"email": user.email})
    safe_token = quote(token, safe="")
    link = f"https://{config.DOMAIN}/api/auth/verify?token={safe_token}"

    template = templates.get_template("verify_email.html")

    html_content = template.render({"username": new_user.username, "link": link})

    message = create_message(
        recepients=[user.email], subject="Verify your email address", body=html_content
    )
    bg_task.add_task(mail.send_message, message)

    return {"message": "A link to verify your account has been sent to your email"}


@auth_router.get("/verify")
async def verify_user(token: str, session: session):
    token_data = decode_url_safe_token(token, mail_service.email_serializer)
    email = token_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.is_verified:
        return JSONResponse(
            content={"message": "Account already verified"},
            status_code=status.HTTP_200_OK,
        )

    await user_service.update_user(user, {"is_verified": True}, session)
    return {"message": "Account verified successfullly"}


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


@auth_router.post("/request-password-reset")
async def request_password_reset(data: PasswordResetRequest, bg_task: BackgroundTasks):
    email = data.email
    token = mail_service.create_password_reset_token(
        {"email": email, "type": "password-reset"}
    )
    safe_token = quote(token, safe="")

    link = f"https://{config.DOMAIN}/api/auth/request-password-reset?token={safe_token}"
    template = templates.get_template("password_reset.html")

    html_content = template.render({"link": link})

    message = create_message(
        recepients=[email], subject="Reset Password", body=html_content
    )
    bg_task.add_task(mail.send_message, message)

    return {"message": "A link to reset your password has been sent to your mail"}


@auth_router.post("/reset-password")
async def reset_password(password: PasswordResetConfirm, token: str, session: session):
    token_data = decode_url_safe_token(token, mail_service.password_reset_serializer)
    if token_data.get("type") != "password-reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )
    email = token_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )
    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not veirfy user"
        )
    if password.new_password != password.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )
    password_hash = hash_password(password.confirm_new_password)
    await user_service.update_user(user, {"password_hash": password_hash}, session)
    return JSONResponse(
        content={"message": "Password reset successful"}, status_code=status.HTTP_200_OK
    )


# test email route
@auth_router.post("/send-mail")
async def send_mail(emails: EmailValidator, bg_task: BackgroundTasks):
    recipients = emails.addresses
    template = templates.get_template("base.html")

    html_content = template.render({"year": dt.now().year})

    message = create_message(
        recepients=recipients,
        subject="Write. Collaborate. Create",
        body=html_content,
    )
    bg_task.add_task(mail.send_message, message)
    return {"message": "Email sent successfully"}
