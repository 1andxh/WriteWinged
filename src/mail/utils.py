import logging
from typing import Any

from itsdangerous import URLSafeTimedSerializer

from ..exceptions import InvalidTokenException


def decode_url_safe_token(
    token: str, serializer: URLSafeTimedSerializer, max_age: int = 3600
) -> dict[str, Any]:
    try:
        return serializer.loads(token, max_age=max_age)
    except Exception as e:
        logging.error(str(e))
        raise InvalidTokenException() from e
