from typing import Annotated
from urllib.parse import quote

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import RedirectResponse

from ..config import config
from ..exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
    WriteWingedException,
)
from .dependencies import (
    auth_service,
    get_current_user,
    mail_service,
    token_service,
    user_service,
)
from .models import User
from .oauth import google_oauth_configured, oauth
from .schemas import (
    GoogleUser,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
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
async def create_user_account(
    payload: UserCreateModel,
    auth_service: auth_service,
    mail_service: mail_service,
    background_tasks: BackgroundTasks,
):
    user = await auth_service.register(payload)
    background_tasks.add_task(mail_service.send_verification_email, user)
    return user


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


@auth_router.get("/verify", response_model=MessageResponse)
async def verify_email(
    token: str, user_service: user_service, mail_service: mail_service
):
    email = mail_service.decode_email_verification_token(token)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise UserNotFoundException()
    if user.is_verified:
        return MessageResponse(message="Account already verified")
    await user_service.update_user(user, {"is_verified": True})
    return MessageResponse(message="Account verified successfully")


@auth_router.post("/request-password-reset", response_model=MessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    user_service: user_service,
    mail_service: mail_service,
    background_tasks: BackgroundTasks,
):
    user = await user_service.get_user_by_email(payload.email)
    if user is not None:
        background_tasks.add_task(mail_service.send_password_reset_email, payload.email)

    return MessageResponse(message="If that email exists, a reset link has been sent")


@auth_router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: PasswordResetConfirm,
    token: str,
    user_service: user_service,
    mail_service: mail_service,
):
    email = mail_service.decode_password_reset_token(token)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise UserNotFoundException()
    await user_service.set_password(user, payload.new_password)
    return MessageResponse(message="Password reset successful")


@auth_router.get("/me", response_model=UserResponse)
async def get_user(user: current_user):
    return user


@auth_router.get("/google", name="google_login")
async def login_via_google(request: Request):
    if not google_oauth_configured():
        raise WriteWingedException(
            "Google OAuth is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    redirect_uri = config.GOOGLE_REDIRECT_URI or str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)  # type: ignore


@auth_router.get("/callback/google", name="google_callback")
async def google_callback(
    request: Request, auth_service: auth_service, token_service: token_service
):
    try:
        token = await oauth.google.authorize_access_token(request)  # type: ignore
    except OAuthError as exc:
        raise InvalidCredentialsException() from exc

    userinfo = token.get("userinfo")
    if userinfo is None:
        raise InvalidCredentialsException()

    google_user = GoogleUser(**userinfo)
    user = await auth_service.authenticate_via_google(google_user)
    tokens = await token_service.issue_token_pair(
        user,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    frontend_url = config.FRONTEND_URL or config.ALLOWED_ORIGINS.split(",")[0].strip()
    redirect_url = (
        f"{frontend_url}/auth/google/callback"
        f"?access_token={quote(tokens.access_token)}"
        f"&refresh_token={quote(tokens.refresh_token)}"
    )
    return RedirectResponse(redirect_url, headers={"Referrer-Policy": "no-referrer"})
