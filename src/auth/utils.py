from fastapi import Depends
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import bcrypt, hashlib
from datetime import datetime, timedelta, timezone
import jwt
import uuid
from src.config import config
from ..db.dependency import session
import logging
from typing import Annotated


from authlib.integrations.starlette_client import OAuth
from ..config import config
from starlette.config import Config

REFRESH_TOKEN_EXPIRY = 2
GOOGLE_CLIENT_ID = config.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = config.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/auth/callback/google"

config_data = {
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
}

starlette_config = Config(environ=config_data)

oauth = OAuth(starlette_config)

oauth.register(
    name="google",
    # client_id=GOOGLE_CLIENT_ID,
    # client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "redirect_url": GOOGLE_REDIRECT_URI,
    },
)

oauth_bearer = OAuth2PasswordBearer(tokenUrl="/token")
jwt_secret_key = config.JWT_SECRET
jwt_algorithm = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRY = 3600

now = datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    hashed = bcrypt.hashpw(digest, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(pasword: str, hashed: str) -> bool:
    digest = hashlib.sha256(pasword.encode("utf-8")).digest()
    return bcrypt.checkpw(digest, hashed.encode("utf-8"))


def create_access_token(
    data: dict,
    expiry: timedelta = timedelta(seconds=ACCESS_TOKEN_EXPIRY),
    refresh: bool = False,
):
    payload = {}

    payload["user"] = data
    payload["exp"] = now + expiry
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh
    payload["iat"] = now

    token = jwt.encode(payload=payload, key=jwt_secret_key, algorithm=jwt_algorithm)
    return token


def decode_token(token: str) -> dict | None:
    try:
        token_data = jwt.decode(token, key=jwt_secret_key, algorithms=[jwt_algorithm])
        return token_data
    except jwt.PyJWTError as e:
        logging.exception(e)


def get_current_user(token: Annotated[str, Depends(oauth_bearer)], session: session):
    pass


def get_tokens(user):
    access_token = create_access_token(
        data={"email": user.email, "user_id": str(user.id), "role": user.role},
        expiry=timedelta(days=7),
    )
    refresh_token = create_access_token(
        data={"email": user.email, "user_id": str(user.id), "role": user.role},
        expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
        refresh=True,
    )

    return access_token, refresh_token
