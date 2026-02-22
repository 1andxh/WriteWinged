from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .config import config
import logging

secret_key = config.MIDDLEWARE_SECRET

logger = logging.getLogger("uvicorn.access")

logger.disabled = True


def register_middleware(app: FastAPI):
    app.add_middleware(
        TrustedHostMiddleware,
        www_redirect=True,
        allowed_hosts=["localhost", "127.0.0.1", "127.0.0.1:6379"],
    )

    app.add_middleware(SessionMiddleware, secret_key)  # required for OAuth to work

    @app.middleware("http")
    async def get_request_info(request: Request, call_next):
        print(f"INCOMING: {request.method} {request.url.path}")

        response = await call_next(request)

        print(f"RESPONSE: STATUS {response.status_code}")
        return response
