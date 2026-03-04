from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .config import config
import logging

secret_key = config.MIDDLEWARE_SECRET

logger = logging.getLogger("uvicorn.access")


def register_middleware(app: FastAPI):
    app.add_middleware(
        TrustedHostMiddleware,
        www_redirect=True,
        allowed_hosts=["localhost", "127.0.0.1", "127.0.0.1:6379"],
    )

    app.add_middleware(SessionMiddleware, secret_key)  # required for OAuth to work

    @app.middleware("http")
    async def get_request_info(request: Request, call_next):
        response = await call_next(request)
        if config.LOG_REQUESTS:
            client = request.client.host if request.client else "-"
            method = request.method
            path = request.url.path
            if request.url.query:
                path = f"{path}?{request.url.query}"
            http_version = request.scope.get("http_version", "1.1")
            status_code = response.status_code
            logger.info(
                '%s - "%s %s HTTP/%s" %d',
                client,
                method,
                path,
                http_version,
                status_code,
            )
        return response
