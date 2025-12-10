from fastapi import APIRouter, Request, status
from authlib.integrations.starlette_client import OAuthError
from .utils import oauth
from ..db.dependency import session
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from .schemas import GoogleUser
from .service import GoogleUserService
from .dependencies import AccessTokenBearer, RefreshTokenBearer
from fastapi.responses import JSONResponse
from .utils import create_access_token, verify_password
from datetime import timedelta
from .models import User

GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/api/auth/callback/google"
REFRESH_TOKEN_EXPIRY = 14

auth_router = APIRouter()
google_user_service = GoogleUserService()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()


print("SESSION TYPE:", type(session))


@auth_router.get("/google", name="google_login")
async def login_via_google(request: Request):
    # url = request.url_for(GOOGLE_REDIRECT_URI)
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)  # type: ignore


print("Google: ", oauth.google)


@auth_router.get("/callback/google", name="google_callback")
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
        # print("Existing user")
        user = is_existing_user
    else:
        # print("Creating user")
        user = await google_user_service.create_user_from_google_info(
            google_user, session, is_verified=True
        )
    # todo: change is_verified at this point
    assert user is not None
    access_token = create_access_token(
        data={"email": user.email, "user_id": str(user.id), "role": user.role},
        expiry=timedelta(days=7),
    )
    refresh_token = create_access_token(
        data={}, expiry=timedelta(days=REFRESH_TOKEN_EXPIRY), refresh=True
    )

    return JSONResponse(
        content={"access_token": access_token, "refresh_token": refresh_token}
    )

    # access_token = create_access_token(user.username, user.id, timedelta(days=7))
    # refresh_token = create_refresh_token(user.username, user.id, timedelta(days=14))

    # return RedirectResponse(
    #     f"{FRONTEND_URL}/auth?access_token={access_token}&refresh_token={refresh_token}"
