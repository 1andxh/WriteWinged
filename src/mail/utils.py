from fastapi import HTTPException, status
from itsdangerous import URLSafeTimedSerializer
from typing import Any
import logging

# nts: too generic
# def create_url_safe_token(data: dict):
#     token = serializer.dumps(data)
#     return token


def decode_url_safe_token(
    token: str, serializer: URLSafeTimedSerializer
) -> dict[str, Any]:
    try:
        token_data = serializer.loads(token, max_age=3600)
        return token_data
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not verify token"
        )
