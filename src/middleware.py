from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .config import config
import logging

logger = logging.getLogger("writewinged.middleware")


def register_middleware(app: FastAPI):
    app.add_middleware(
        TrustedHostMiddleware,
        www_redirect=True,
        allowed_hosts=["localhost", "127.0.0.1", "127.0.0.1:6379"],
    )

    app.add_middleware(
        SessionMiddleware, secret_key=config.MIDDLEWARE_SECRET
    )  # required for OAuth to work

    @app.middleware("http")
    async def get_request_info(request: Request, call_next):
        if config.LOG_REQUESTS:
            logger.info("incoming request %s %s", request.method, request.url.path)

        response = await call_next(request)

        if config.LOG_REQUESTS:
            logger.info("response status %s", response.status_code)
        return response
