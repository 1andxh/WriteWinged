import logging
from typing import Any

from itsdangerous import URLSafeTimedSerializer

from ..exceptions import InvalidTokenException


def decode_url_safe_token(
    token: str, serializer: URLSafeTimedSerializer
) -> dict[str, Any]:
    try:
        return serializer.loads(token, max_age=3600)
    except Exception as e:
        logging.error(str(e))
        raise InvalidTokenException() from e
