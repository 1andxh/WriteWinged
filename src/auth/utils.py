import bcrypt
import hashlib
from datetime import datetime, timedelta, timezone
import jwt
import uuid
from src.config import config
import logging


jwt_secret_key = config.JWT_SECRET
jwt_algorithm = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRY = 3600


def hash_password(password: str) -> str:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    hashed = bcrypt.hashpw(digest, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return bcrypt.checkpw(digest, hashed.encode("utf-8"))


def create_access_token(
    data: dict,
    expiry: timedelta = timedelta(seconds=ACCESS_TOKEN_EXPIRY),
):
    now = datetime.now(timezone.utc)
    payload = {}

    payload["user"] = data
    payload["exp"] = now + expiry
    payload["jti"] = str(uuid.uuid4())
    payload["iat"] = now

    token = jwt.encode(payload=payload, key=jwt_secret_key, algorithm=jwt_algorithm)
    return token


def decode_token(token: str) -> dict | None:
    try:
        token_data = jwt.decode(token, key=jwt_secret_key, algorithms=[jwt_algorithm])
        return token_data
    except jwt.PyJWTError as e:
        logging.exception(e)


def get_access_token(user):
    return create_access_token(
        data={"email": user.email, "user_id": str(user.id), "role": user.role},
        expiry=timedelta(days=7),
    )
