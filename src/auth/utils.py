from passlib.context import CryptContext
import bcrypt, hashlib
from datetime import datetime, timedelta, timezone
import jwt
from src.config import Config
import uuid
from src.config import config
import logging

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
