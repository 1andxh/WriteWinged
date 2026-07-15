import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import jwt
import uuid
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from pydantic import ValidationError
from src.config import config
from .schemas import TokenPayload
import logging

jwt_secret_key = config.JWT_SECRET
jwt_algorithm = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRY = timedelta(minutes=30)
REFRESH_TOKEN_EXPIRY = timedelta(days=30)

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except VerificationError:
        return False


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    expiry = now + ACCESS_TOKEN_EXPIRY

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(payload=payload, key=jwt_secret_key, algorithm=jwt_algorithm)


def decode_token(token: str) -> TokenPayload | None:
    try:
        raw_payload = jwt.decode(token, key=jwt_secret_key, algorithms=[jwt_algorithm])
        return TokenPayload(**raw_payload)
    except (jwt.PyJWTError, ValidationError) as e:
        logging.exception(e)
        return None
